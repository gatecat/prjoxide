use crate::chip::*;
use crate::database::*;

use std::fs::File;
use std::io::Read;

pub struct BitstreamParser {
    data: Vec<u8>,
    index: usize,
    crc16: u16,
    verbose: bool,
}

// Magic sequences
const COMMENT_START: [u8; 2] = [0xFF, 0x00];
const COMMENT_END: [u8; 2] = [0x00, 0xFF];
const PREAMBLE: [u8; 4] = [0xFF, 0xFF, 0xBD, 0xB3];

// Commands
const SPI_MODE: u8 = 0b01111001;
const JUMP: u8 = 0b01111110;
const LSC_RESET_CRC: u8 = 0b00111011;
const VERIFY_ID: u8 = 0b11100010;
const LSC_WRITE_COMP_DIC: u8 = 0b00000010;
const LSC_PROG_CNTRL0: u8 = 0b00100010;
const LSC_INIT_ADDRESS: u8 = 0b01000110;
const LSC_WRITE_ADDRESS: u8 = 0b10110100;
const LSC_PROG_INCR_CMP: u8 = 0b10111000;
const LSC_PROG_INCR_RTI: u8 = 0b10000010;
const LSC_PROG_SED_CRC: u8 = 0b10100010;
const ISC_PROGRAM_SECURITY: u8 = 0b11001110;
const ISC_PROGRAM_USERCODE: u8 = 0b11000010;
const LSC_EBR_ADDRESS: u8 = 0b11110110;
const LSC_EBR_WRITE: u8 = 0b10110010;
const ISC_PROGRAM_DONE: u8 = 0b01011110;
const LSC_POWER_CTRL: u8 = 0b001010110;
const DUMMY: u8 = 0b11111111;

// CRC16 constants
const CRC16_POLY: u16 = 0x8005;
const CRC16_INIT: u16 = 0x0000;

impl BitstreamParser {
    pub fn new(bitstream: &[u8]) -> BitstreamParser {
        BitstreamParser {
            data: bitstream.to_vec(),
            index: 0,
            crc16: CRC16_INIT,
            verbose: false,
        }
    }

    pub fn parse_file(db: &mut Database, filename: &str) -> Result<Chip, &'static str> {
        let mut f = File::open(filename).map_err(|_x| "failed to open file")?;
        let mut buffer = Vec::new();
        // read the whole file
        f.read_to_end(&mut buffer)
            .map_err(|_x| "failed to read file")?;
        let mut parser = BitstreamParser::new(&buffer);
        let mut c = parser.parse(db)?;
        c.cram_to_tiles();
        Ok(c)
    }

    // Add a single byte to the running CRC16 accumulator
    fn update_crc16(&mut self, val: u8) {
        let mut bit_flag = 0;
        for i in (0..8).rev() {
            bit_flag = self.crc16 >> 15;
            self.crc16 <<= 1;
            self.crc16 |= ((val >> i) & 1) as u16;
            if bit_flag != 0 {
                self.crc16 ^= CRC16_POLY;
            }
        }
    }
    // Get a single byte, updating the CRC
    fn get_byte(&mut self) -> u8 {
        let val = self.data[self.index];
        self.index += 1;
        self.update_crc16(val);
        return val;
    }
    // Gets an opcode byte, updating the CRC if it isn't a dummy opcode (0xFF
    fn get_opcode_byte(&mut self) -> u8 {
        let val = self.data[self.index];
        self.index += 1;
        if val != DUMMY {
            self.update_crc16(val);
        }
        return val;
    }
    // Checks if the stream matches a preamble token, consuming
    // the token and returning true if it does
    fn check_preamble(&mut self, preamble: &[u8]) -> bool {
        if (self.index + preamble.len()) > self.data.len() {
            return false;
        }
        if &self.data[self.index..self.index + preamble.len()] == preamble {
            self.index += preamble.len();
            return true;
        } else {
            return false;
        }
    }
    // Get a 16-bit big-endian word
    fn get_u16(&mut self) -> u16 {
        let mut val = (self.get_byte() as u16) << 8;
        val |= self.get_byte() as u16;
        return val;
    }
    // Get a 32-bit big-endian word
    fn get_u32(&mut self) -> u32 {
        let mut val = (self.get_byte() as u32) << 24;
        val |= (self.get_byte() as u32) << 16;
        val |= (self.get_byte() as u32) << 8;
        val |= self.get_byte() as u32;
        return val;
    }
    // Copy bytes
    fn copy_bytes(&mut self, dest: &mut [u8]) {
        for i in 0..dest.len() {
            dest[i] = self.get_byte();
        }
    }
    // Skip bytes
    fn skip_bytes(&mut self, len: usize) {
        for i in 0..len {
            self.get_byte();
        }
    }
    // "Push out" last 16 bits to get final crc16
    fn finalise_crc16(&mut self) {
        let mut bit_flag = 0;
        for i in 0..16 {
            bit_flag = (self.crc16 >> 15) & 0x1;
            self.crc16 <<= 1;
            if bit_flag == 0x1 {
                self.crc16 ^= CRC16_POLY;
            }
        }
    }

    // Consume and check crc16
    fn check_crc16(&mut self) {
        self.finalise_crc16();
        let calc_crc16 = self.crc16;
        let exp_crc16 = self.get_u16();
        assert_eq!(calc_crc16, exp_crc16);
        self.crc16 = CRC16_INIT;
    }

    fn done(&self) -> bool {
        self.index >= self.data.len()
    }

    // Process bitstream container
    // Consumes metadata up to and including preamble
    fn parse_container(&mut self) -> Result<(), &'static str> {
        let mut in_metadata = false;
        let mut curr_meta = String::new();
        while !self.done() {
            if self.check_preamble(&PREAMBLE) {
                println!("bitstream start at {}", self.index);
                return Ok(());
            }
            if !in_metadata && self.check_preamble(&COMMENT_START) {
                in_metadata = true;
                continue;
            }
            if in_metadata && self.check_preamble(&COMMENT_END) {
                in_metadata = false;
                continue;
            }
            if in_metadata {
                let ch = self.get_byte();
                if ch == 0x00 {
                    if curr_meta.len() > 0 {
                        println!("Metadata: {}", &curr_meta);
                    }
                    curr_meta.clear();
                } else {
                    curr_meta.push(ch as char);
                }
            } else {
                self.get_byte();
            }
        }
        Err("failed to find preamble")
    }

    // Parse the bitstream itself
    fn parse_bitstream(&mut self, db: &mut Database) -> Result<Chip, &'static str> {
        let mut curr_frame = 0;
        let mut curr_chip = None;
        while !self.done() {
            let cmd = self.get_opcode_byte();
            match cmd {
                LSC_RESET_CRC => {
                    println!("reset CRC");
                    self.skip_bytes(3);
                    self.crc16 = CRC16_INIT;
                }
                LSC_PROG_CNTRL0 => {
                    self.skip_bytes(3);
                    let ctrl0 = self.get_u32();
                    println!("set CTRL0 to 0x{:08X}", ctrl0);
                }
                VERIFY_ID => {
                    self.skip_bytes(3);
                    let idcode = self.get_u32();
                    curr_chip = Some(Chip::from_idcode(db, idcode));
                    println!("check IDCODE is 0x{:08X}", idcode);
                }
                LSC_INIT_ADDRESS => {
                    self.skip_bytes(3);
                    println!("reset frame address");
                    curr_frame = 0;
                }
                LSC_WRITE_ADDRESS => {
                    self.skip_bytes(3);
                    curr_frame = self.get_u32();
                    println!("set frame address to 0x{:08X}", curr_frame);
                }
                LSC_PROG_INCR_RTI => {
                    let cfg = self.get_byte();
                    let count = self.get_u16();
                    let bits_per_frame: usize;
                    let pad_bits: usize;
                    let chip: &mut Chip;
                    match curr_chip.as_mut() {
                        Some(ch) => {
                            bits_per_frame = ch.data.bits_per_frame;
                            pad_bits = ch.data.frame_ecc_bits + ch.data.pad_bits_after_frame;
                            chip = ch;
                        }
                        None => {
                            return Err("got bitstream before idcode");
                        }
                    }
                    println!("write {} frames at 0x{:08x}", count, curr_frame);
                    let mut frame_bytes = vec![0 as u8; (bits_per_frame + 7) / 8 + 2];
                    assert_eq!(cfg, 0x91);
                    for _ in 0..count {
                        self.copy_bytes(&mut frame_bytes);
                        for j in 0..bits_per_frame {
                            let ofs = (j + pad_bits) as usize;
                            if ((frame_bytes[(frame_bytes.len() - 1) - (ofs / 8)] >> (ofs % 8))
                                & 0x01)
                                == 0x01
                            {
                                let decoded_frame = chip.frame_addr_to_idx(curr_frame);
                                if decoded_frame < chip.cram.frames {
                                    // FIXME: frame addressing
                                    chip.cram.set(decoded_frame, j, true);
                                }
                                if self.verbose {
                                    println!("F0x{:08x}B{:04}", curr_frame, j);
                                }
                            }
                        }
                        let parity = (frame_bytes[frame_bytes.len() - 1] as u16) << 8
                            | (frame_bytes[frame_bytes.len() - 2] as u16);
                        if self.verbose {
                            for j in 0..14 {
                                if (parity >> j) & 0x1 == 0x1 {
                                    println!("F0x{:08x}P{:02}", curr_frame, j);
                                }
                            }
                        }
                        self.check_crc16();
                        let d = self.get_byte();
                        assert_eq!(d, 0xFF);
                        curr_frame += 1;
                    }
                }
                LSC_POWER_CTRL => {
                    self.skip_bytes(2);
                    let pwr = self.get_byte();
                    println!("power control: {}", pwr);
                }
                ISC_PROGRAM_USERCODE => {
                    let cmp_crc = self.get_byte() & 0x80 == 0x80;
                    self.skip_bytes(2);
                    let usercode = self.get_u32();
                    println!("set usercode to 0x{:08X}", usercode);
                    if cmp_crc {
                        self.check_crc16();
                    }
                }
                ISC_PROGRAM_DONE => {
                    self.skip_bytes(3);
                    println!("done");
                }
                DUMMY => {}
                _ => {
                    println!("unknown command 0x{:02X} at {}", cmd, self.index);
                    return Err("unknown bitstream command");
                }
            }
        }
        match curr_chip {
            Some(x) => Ok(x),
            None => Err("missing bitstream content"),
        }
    }

    pub fn parse(&mut self, db: &mut Database) -> Result<Chip, &'static str> {
        self.parse_container()?;
        let c = self.parse_bitstream(db)?;
        Ok(c)
    }
}
