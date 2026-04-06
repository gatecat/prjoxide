use crate::chip::*;
use crate::database::*;

use std::convert::TryInto;
use std::fs::File;
use std::io::{BufReader, Read};
use flate2::read::GzDecoder;
use log::{debug, warn};

pub struct BitstreamParser {
    data: Vec<u8>,
    index: usize,
    crc16: u16,
    ecc14: u16,
    verbose: bool,
    metadata: Vec<String>,
    comp_dic: [u8; 16],
}

// Magic sequences
const COMMENT_START: [u8; 2] = [0xFF, 0x00];
const COMMENT_END: [u8; 2] = [0x00, 0xFF];
const COMMENT_END_RDBK: [u8; 2] = [0x00, 0xFE];
const PREAMBLE: [u8; 4] = [0xFF, 0xFF, 0xBD, 0xB3];
const PREAMBLE_IP_EVAL: [u8; 4] = [0xFF, 0xFF, 0xBE, 0xB3];

// Commands

#[allow(dead_code)]
const SPI_MODE: u8 = 0b01111001;

#[allow(dead_code)]
const JUMP: u8 = 0b01111110;

const LSC_RESET_CRC: u8 = 0b00111011;
const VERIFY_ID: u8 = 0b11100010;

#[allow(dead_code)]
const LSC_WRITE_COMP_DIC: u8 = 0b00000010;
const LSC_READ_CNTRL0: u8 = 0b00100000;
const LSC_PROG_CNTRL0: u8 = 0b00100010;
const LSC_INIT_ADDRESS: u8 = 0b01000110;
const LSC_WRITE_ADDRESS: u8 = 0b10110100;

#[allow(dead_code)]
const LSC_PROG_INCR_CMP: u8 = 0b10111000;
const LSC_PROG_INCR_RTI: u8 = 0b10000010;

#[allow(dead_code)]
const LSC_PROG_SED_CRC: u8 = 0b10100010;

#[allow(dead_code)]
const ISC_PROGRAM_SECURITY: u8 = 0b11001110;
const ISC_PROGRAM_USERCODE: u8 = 0b11000010;
const LSC_BUS_ADDRESS: u8 = 0b11110110;
const LSC_BUS_WRITE: u8 = 0b01110010;
const ISC_PROGRAM_DONE: u8 = 0b01011110;
const LSC_POWER_CTRL: u8 = 0b001010110;
const DUMMY: u8 = 0b11111111;

// Signing related (we just ignore)
const LSC_AUTH_CTRL: u8 = 0b01011000;

// Read the dry-run User Electronic Signature shadow register.
const LSC_READ_DR_UES: u8 = 0b01011101;

// CRC16 constants
const CRC16_POLY: u16 = 0x8005;
const CRC16_INIT: u16 = 0x0000;

// ECC constants
const ECC_POLY: u16 = 0x202D;
const ECC_INIT: u16 = 0x0000;

enum BitstreamType {
    NORMAL,
    READBACK
}

impl BitstreamParser {
    pub fn new(bitstream: &[u8]) -> BitstreamParser {
        BitstreamParser {
            data: bitstream.to_vec(),
            index: 0,
            crc16: CRC16_INIT,
            ecc14: ECC_INIT,
            verbose: false,
            metadata: Vec::new(),
            comp_dic: [0; 16],
        }
    }

    pub fn parse_file(db: &mut Database, filename: &str) -> Result<Chip, String> {
        let mut f = File::open(filename).map_err(|x| format!("failed to open file {}: {:?}", filename, x) )?;

        let mut buffer = Vec::new();

        if filename.ends_with(".gz") {
            let reader = BufReader::new(f);
            let mut gz = GzDecoder::new(reader);
            gz.read_to_end(&mut buffer)
        } else {
            f.read_to_end(&mut buffer)
        }.map_err(|x| format!("failed to read file {filename}: {x:?}"))?;

        let mut parser = BitstreamParser::new(&buffer);
        let mut c = parser.parse(db)?;
        c.cram_to_tiles();
        Ok(c)
    }

    pub fn serialise_chip(ch: &Chip) -> Vec<u8> {
        let mut b = BitstreamParser {
            data: Vec::new(),
            index: 0,
            crc16: CRC16_INIT,
            ecc14: ECC_INIT,
            verbose: false,
            metadata: Vec::new(),
            comp_dic: [0; 16],
        };
        b.write_string("LSCC"); // magic
        b.write_bytes(&COMMENT_START); // metadata start
        for (i, m) in ch.metadata.iter().enumerate() {
            b.write_string(m);
            if i < (ch.metadata.len() - 1) {
                b.write_byte(0x00); // terminator
            }
        }
        b.write_bytes(&COMMENT_END); // metadata end
        b.write_bytes(&PREAMBLE); // actual bitstream preamble
        b.write_padding(20);
        // Reset CRC, twice for some reason
        b.write_byte(LSC_RESET_CRC);
        b.write_zeros(3);
        b.crc16 = CRC16_INIT;
        b.write_padding(4);
        b.write_byte(LSC_RESET_CRC);
        b.write_zeros(3);
        b.crc16 = CRC16_INIT;
        b.write_padding(4);
        // IDCODE check
        b.write_byte(VERIFY_ID);
        b.write_zeros(3);
        b.write_u32(ch.get_idcode());
        // Set CTRL0
        let mut ctrl0 = 0x00000000;
        let mut compress = false;
        for (k, v) in ch.settings.iter() {
            if k == "background" && v == "1" {
                ctrl0 |= 0x27800000;
            }
            if k == "multiboot" && v == "1" {
                ctrl0 |= 1 << 19;
            }
            if k == "compress" && v == "1" {
                compress = true;
            }
        }
        b.write_byte(LSC_PROG_CNTRL0);
        b.write_zeros(3);
        b.write_u32(ctrl0);
        if compress {
            b.compute_comp_dic(ch);
            b.write_byte(LSC_WRITE_COMP_DIC);
            b.write_zeros(3);
            for i in 0..16 {
                b.write_byte(b.comp_dic[i]);
            }
        }
        // Write "IO" frames
        b.write_frame_addr(0x8000);
        if compress {
            b.write_comp_frames(ch, 0x8000, 32);
        } else {
            b.write_frames(ch, 0x8000, 32);
        }
        b.write_padding(17);
        // Write main frames
        b.write_byte(LSC_INIT_ADDRESS);
        b.write_zeros(3);
        if compress {
            b.write_comp_frames(ch, 0x0000, ch.data.frames - (32 + ch.tap_frame_count));
        } else {
            b.write_frames(ch, 0x0000, ch.data.frames - (32 + ch.tap_frame_count));
        }
        b.write_padding(17);
        // Write tap frames
        b.write_frame_addr(0x8020);
        if compress {
            b.write_comp_frames(ch, 0x8020, ch.tap_frame_count);
        } else {
            b.write_frames(ch, 0x8020, ch.tap_frame_count);
        }
        b.write_padding(17);
        // Write power control
        b.write_byte(LSC_POWER_CTRL);
        b.write_zeros(2);
        b.write_byte(0x01);
        b.write_padding(512);
        // Write IP config
        b.write_ip_config(ch);
        // Write usercode
        b.write_byte(ISC_PROGRAM_USERCODE);
        b.write_byte(0x80); // CRC check enable flag
        b.write_zeros(2);
        b.write_u32(0x00000000);
        b.insert_crc();
        b.write_padding(15);
        // Program DONE
        b.write_byte(ISC_PROGRAM_DONE);
        b.write_zeros(3);
        b.write_padding(4);
        return b.data;
    }

    // Add a single byte to the running CRC16 accumulator
    fn update_crc16(&mut self, val: u8) {
        let mut bit_flag;
        for i in (0..8).rev() {
            bit_flag = self.crc16 >> 15;
            self.crc16 <<= 1;
            self.crc16 |= ((val >> i) & 1) as u16;
            if bit_flag != 0 {
                self.crc16 ^= CRC16_POLY;
            }
        }
    }
    // Add a single *bit* to the frame ECC
    fn update_ecc(&mut self, val: bool) {
        let bit_flag = self.ecc14 >> 13;
        self.ecc14 = ((self.ecc14 << 1) | (val as u16)) & 0x3FFF;
        if bit_flag != 0 {
            self.ecc14 ^= ECC_POLY;
        }
    }
    // Finalise and return ECC
    fn finalise_ecc(&mut self) -> u16 {
        for _i in 0..14 {
            self.update_ecc(false);
        }
        return self.ecc14;
    }

    // Get a single byte, updating the CRC
    fn get_byte(&mut self) -> u8 {
        let val = self.data[self.index];
        self.index += 1;
        self.update_crc16(val);
        return val;
    }
    // Write a byte into the bitstream, updating the CRC
    fn write_byte(&mut self, b: u8) {
        self.data.push(b);
        self.update_crc16(b);
    }
    // Write a byte into the bitstream, without updating the CRC
    fn write_byte_nocrc(&mut self, b: u8) {
        self.data.push(b);
    }
    // Gets an opcode byte, updating the CRC if it isn't a dummy opcode (0xFF)
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
    // Write a 16-bit big-endian word
    fn write_u16(&mut self, h: u16) {
        self.write_byte(((h >> 8) & 0xFF) as u8);
        self.write_byte((h & 0xFF) as u8);
    }
    // Write a 32-bit big-endian word
    fn write_u32(&mut self, w: u32) {
        self.write_byte(((w >> 24) & 0xFF) as u8);
        self.write_byte(((w >> 16) & 0xFF) as u8);
        self.write_byte(((w >> 8) & 0xFF) as u8);
        self.write_byte((w & 0xFF) as u8);
    }
    // Copy bytes
    fn copy_bytes(&mut self, dest: &mut [u8]) {
        for i in 0..dest.len() {
            dest[i] = self.get_byte();
        }
    }
    // Skip bytes
    fn skip_bytes(&mut self, len: usize) {
        for _ in 0..len {
            self.get_byte();
        }
    }
    // Write a number of zeroes into the bitstream
    fn write_zeros(&mut self, len: usize) {
        for _ in 0..len {
            self.write_byte(0x00);
        }
    }
    // Write a number of padding commands into the bitstream
    fn write_padding(&mut self, len: usize) {
        for _ in 0..len {
            self.write_byte_nocrc(0xFF);
        }
    }
    // Add a string into the bitstream
    fn write_string(&mut self, s: &str) {
        self.data.extend(s.bytes());
    }
    // Writes a vec of bytes into the bitstream
    fn write_bytes(&mut self, bytes: &[u8]) {
        for b in bytes {
            self.write_byte(*b);
        }
    }
    fn write_frame_addr(&mut self, addr: u32) {
        self.write_byte(LSC_WRITE_ADDRESS);
        self.write_zeros(3);
        self.write_u32(addr);
    }
    fn write_frames(&mut self, c: &Chip, start_addr: u32, count: usize) {
        self.write_byte(LSC_PROG_INCR_RTI);
        self.write_byte(0x91); // frame load settings
        self.write_u16(count.try_into().unwrap());
        let bits_per_frame = c.data.bits_per_frame;
        let pad_bits = c.data.frame_ecc_bits + c.data.pad_bits_after_frame;
        let mut frame_bytes = vec![0 as u8; (bits_per_frame + 14 + 7) / 8];
        let total_frame_bytes = frame_bytes.len();
        for f in 0..count {
            let frame_addr: u32 = start_addr + (f as u32);
            let frame_idx = c.frame_addr_to_idx(frame_addr);
            self.ecc14 = ECC_INIT;
            for b in frame_bytes.iter_mut() {
                *b = 0;
            }
            for j in (0..bits_per_frame).rev() {
                let ofs = (j + pad_bits) as usize;
                let value = c.cram.get(frame_idx, j);
                self.update_ecc(value);
                if value {
                    frame_bytes[(total_frame_bytes - 1) - (ofs / 8)] |= 1 << (ofs % 8);
                }
            }
            let ecc = self.finalise_ecc();
            frame_bytes[total_frame_bytes - 2] |= ((ecc >> 8) & 0x3F) as u8;
            frame_bytes[total_frame_bytes - 1] |= (ecc & 0xFF) as u8;
            self.write_bytes(&frame_bytes);
            self.insert_crc();
            self.write_byte(0xFF);
        }
    }
    fn write_comp_frames(&mut self, c: &Chip, start_addr: u32, count: usize) {
        self.write_byte(LSC_PROG_INCR_CMP);
        self.write_byte(0xD4); // frame load settings
        self.write_u16(count.try_into().unwrap());
        let bits_per_frame = c.data.bits_per_frame;
        let pad_bits = c.data.frame_ecc_bits + c.data.pad_bits_after_frame;
        let mut frame_bytes = vec![0 as u8; 8 * ((bits_per_frame + 14 + 63) / 64)];
        let total_frame_bytes = frame_bytes.len();
        for f in 0..count {
            let frame_addr: u32 = start_addr + (f as u32);
            let frame_idx = c.frame_addr_to_idx(frame_addr);
            self.ecc14 = ECC_INIT;
            for b in frame_bytes.iter_mut() {
                *b = 0;
            }
            for j in (0..bits_per_frame).rev() {
                let ofs = (j + pad_bits) as usize;
                let value = c.cram.get(frame_idx, j);
                self.update_ecc(value);
                if value {
                    frame_bytes[(total_frame_bytes - 1) - (ofs / 8)] |= 1 << (ofs % 8);
                }
            }
            let ecc = self.finalise_ecc();
            frame_bytes[total_frame_bytes - 2] |= ((ecc >> 8) & 0x3F) as u8;
            frame_bytes[total_frame_bytes - 1] |= (ecc & 0xFF) as u8;
            self.write_comp_frame(&frame_bytes);
            if f == count - 1 {
                self.insert_crc();
            }
            for _ in 0..4 {
                self.write_byte(0xFF);
            }
        }
    }
    fn compute_comp_dic(&mut self, c: &Chip) {
        // precompute all frames to discover the 16 most common byte values for the dictionary
        let mut histogram = [0 as usize; 256]; 
        let bits_per_frame = c.data.bits_per_frame;
        let pad_bits = c.data.frame_ecc_bits + c.data.pad_bits_after_frame;
        let mut frame_bytes = vec![0 as u8; (bits_per_frame + 14 + 7) / 8];
        let total_frame_bytes = frame_bytes.len();
        for f in 0..c.cram.frames {
            self.ecc14 = ECC_INIT;
            for b in frame_bytes.iter_mut() {
                *b = 0;
            }
            for j in (0..bits_per_frame).rev() {
                let ofs = (j + pad_bits) as usize;
                let value = c.cram.get(f, j);
                if value {
                    frame_bytes[(total_frame_bytes - 1) - (ofs / 8)] |= 1 << (ofs % 8);
                }
            }
            for b in &frame_bytes {
                histogram[*b as usize] += 1;
            }
        }
        let mut pairs = [(0 as usize, 0 as u8); 256];
        for i in 0..256 {
            pairs[i] = (histogram[i], i as u8);
        }
        pairs.sort();
        for i in 0..16 {
            self.comp_dic[i] = pairs[240 + i].1;
        }
    }

    fn write_ip_config(&mut self, c: &Chip) {
        // Create continguous chunks
        let mut last_addr = None;
        let mut curr_chunk : Option<(u32, Vec<u8>)> = None;
        let mut chunks = Vec::new();
        // The 0x0E000000 region is special
        for (&addr, &val) in c.ipconfig.iter().filter(|(&a, _)| a & 0xFF000000 != 0x0E000000 ) {
            if last_addr.is_none() || (last_addr.unwrap() + 1 != addr)
                || (curr_chunk.is_some() && curr_chunk.as_ref().unwrap().1.len() >= 40960) {
                // All cases where we start a new chunk
                if curr_chunk.is_some() {
                    chunks.push(curr_chunk.unwrap());
                }
                curr_chunk = Some((addr, Vec::new()));
            }
            curr_chunk.as_mut().unwrap().1.push(val);
            last_addr = Some(addr);
        }
        if curr_chunk.is_some() {
            chunks.push(curr_chunk.unwrap());
        }
        // PLL bits are written seperately, in reverse order for some reason
        for (&addr, &val) in c.ipconfig.iter().filter(|(&a, _)| a & 0xFF000000 == 0x0E000000 ).rev() {
            chunks.push((addr, vec![val]))
        }
        // Write out chunks
        for (start, bytes) in chunks {
            // Write address
            self.write_byte(LSC_BUS_ADDRESS);
            self.write_zeros(3);
            let mut adj_addr = start;
            // Fixup LRAM addressing
            if adj_addr & 0xFF000000 == 0x2E000000 {
                let ls = adj_addr & 0x1FFFF;
                let ms = adj_addr & 0xFFFE0000;
                adj_addr = ms | ((ls * 8) / 10);
            }
            self.write_u32(adj_addr);
            // Padding
            self.write_padding(9);
            // Write data
            let frame_size = c.get_bus_frame_size(start);
            let frame_count = (bytes.len() + frame_size - 1) / frame_size;
            self.write_byte(LSC_BUS_WRITE);
            self.write_byte(0xD0); // check CRC
            self.write_u16(frame_count.try_into().unwrap());
            let total_bytes = frame_size * frame_count;
            for i in 0..total_bytes {
                if i <  bytes.len() {
                    self.write_byte(bytes[i]);
                } else {
                    self.write_byte(0x00);
                }
            }
            self.insert_crc();
        }
    }
    // "Push out" last 16 bits to get final crc16
    fn finalise_crc16(&mut self) {
        let mut bit_flag;
        for _i in 0..16 {
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

    // Finalise and insert CRC
    fn insert_crc(&mut self) {
        self.finalise_crc16();
        self.write_u16(self.crc16);
        self.crc16 = CRC16_INIT;
    }

    fn done(&self) -> bool {
        self.index >= self.data.len()
    }

    // Process bitstream container
    // Consumes metadata up to and including preamble
    fn parse_container(&mut self) -> Result<BitstreamType, &'static str> {
        let mut in_metadata = false;
        let mut curr_meta = String::new();
        while !self.done() {
            if self.check_preamble(&PREAMBLE) {
                debug!("bitstream start at {}", self.index);
                return Ok(BitstreamType::NORMAL);
            }
            if self.check_preamble(&PREAMBLE_IP_EVAL) {
                debug!("bitstream (ip eval) start at {}", self.index);
                return Ok(BitstreamType::NORMAL);
            }	    
            if !in_metadata && self.check_preamble(&COMMENT_START) {
                in_metadata = true;
                continue;
            }
            if in_metadata && self.check_preamble(&COMMENT_END) {
                if curr_meta.len() > 0 {
                    self.metadata.push(curr_meta.to_string());
 		    if curr_meta.is_ascii() {
                       debug!("Metadata: {}", &curr_meta);
		    } else {
                       warn!("Warning: Metadata of len {} contains non ascii data", curr_meta.len());
                    } 		    
                    curr_meta.clear();
                }
                in_metadata = false;
                continue;
            }
            if in_metadata && self.check_preamble(&COMMENT_END_RDBK) {
                if curr_meta.len() > 0 {
                    self.metadata.push(curr_meta.to_string());
                    curr_meta.clear();
                }
                return Ok(BitstreamType::READBACK);
            }
            if in_metadata {
                let ch = self.get_byte();
                if ch == 0x00 {
                    if curr_meta.len() > 0 {
		        if curr_meta.is_ascii() {
                            debug!("Metadata: {}", &curr_meta);
			} else {
                            warn!("Warning: Metadata of len {} contains non ascii data", curr_meta.len());
                        }
                    }
                    self.metadata.push(curr_meta.to_string());
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

    fn decompress_frame(&mut self, dest: &mut [u8]) {
        let mut read_data : u16 = 0;
        let mut remaining_bits : usize = 0;
        // Based on the implementation in trellis

        // Every byte can be encoded by on of 4 cases
        // It's a prefix-free code so we can identify each one just by looking at the first bits:
        // 0 -> Byte zero (0000 0000)
        // 10 xxxx -> Stored byte in compression_dict, xxxx is the index (0-15)
        // 11 xxxxxxxx -> Literal byte, xxxxxxxx is the encoded byte

        for i in 0..dest.len() {
            if remaining_bits == 0 {
                read_data = self.get_byte() as u16;
                remaining_bits = 8;
            }
            let mut next_bit = ((read_data >> (remaining_bits - 1)) & 1) == 1;
            remaining_bits -= 1;
            dest[i] = if next_bit {
                if remaining_bits < 5 {
                    read_data = (read_data << 8) | (self.get_byte() as u16);
                    remaining_bits += 8;
                }
                next_bit = (read_data >> (remaining_bits-1) & 1) == 1;
                remaining_bits -= 1;
                if next_bit {
                    // 11 xxxx xxxx: Literal byte, just read the next 8 bits & use that
                    // we consumed 10 bits total
                    if remaining_bits < 8 {
                        read_data = (read_data << 8) | (self.get_byte() as u16);
                        remaining_bits += 8;
                    }
                    let literal = ((read_data >> (remaining_bits - 8)) & 0xff) as u8;
                    remaining_bits -= 8;
                    literal
                } else {
                    // Starts with 10, it is a stored literal
                    // 10 xxxx
                    let idx = ((read_data >> (remaining_bits-4)) & 0xf) as usize;
                    remaining_bits -= 4;
                    self.comp_dic[15 - idx]
                }
            } else {
                // 0: literal 0 byte
                0
            };
        }
    }

    fn write_comp_frame(&mut self, frame: &[u8]) {
        let mut buffer : u8 = 0;
        let mut bits_in_buffer : usize = 0;
        for b in frame {
            let mut add_bit = |s: &mut Self, bit: bool| {
                if bit {
                    buffer |= 1 << (7 - bits_in_buffer);
                }
                bits_in_buffer += 1;
                if bits_in_buffer == 8 {
                    s.write_byte(buffer);
                    bits_in_buffer = 0;
                    buffer = 0;
                }
            };
            let mut add_bits = |s: &mut Self, value: u16, len: usize| {
                for i in (0..len).rev() {
                    add_bit(s, (value & (1 << i)) != 0);
                }

            };
            if *b == 0 {
                // 0 byte -> 0 bit
                add_bit(self, false);
                continue;
            }
            let mut dict_found = false;
            for i in 0..16 {
                if self.comp_dic[i] == *b {
                    // dictionary entry -> 0b10xxxx
                    add_bits(self, 0b10, 2);
                    add_bits(self, (15 - i) as u16, 4);
                    dict_found = true;
                    break;
                }
            }
            if dict_found {
                continue;
            }
            // literal -> 0b11xxxxxxxx
            add_bits(self, 0b11, 2);
            add_bits(self, *b as u16, 8);
        }
        if bits_in_buffer != 0 {
            self.write_byte(buffer);
        }
    }

    // Parse the bitstream itself
    fn parse_bitstream(&mut self, db: &mut Database) -> Result<Chip, &'static str> {
        let mut curr_frame = 0;
        let mut bus_addr = 0;
        let mut curr_chip = None;
        while !self.done() {
            let cmd = self.get_opcode_byte();
            match cmd {
                LSC_RESET_CRC => {
                    debug!("reset CRC");
                    self.skip_bytes(3);
                    self.crc16 = CRC16_INIT;
                }
                LSC_PROG_CNTRL0 => {
                    self.skip_bytes(3);
                    let ctrl0 = self.get_u32();
                    debug!("set CTRL0 to 0x{:08X}", ctrl0);
                }
                VERIFY_ID => {
                    self.skip_bytes(3);
                    let idcode = self.get_u32();
                    let mut chip = Chip::from_idcode(db, idcode);
                    chip.metadata = self.metadata.clone();
                    curr_chip = Some(chip);
                    debug!("check IDCODE is 0x{:08X}", idcode);
                }
                LSC_INIT_ADDRESS => {
                    self.skip_bytes(3);
                    debug!("reset frame address");
                    curr_frame = 0;
                }
                LSC_WRITE_ADDRESS => {
                    self.skip_bytes(3);
                    curr_frame = self.get_u32();
                    debug!("set frame address to 0x{:08X}", curr_frame);
                }
                LSC_AUTH_CTRL => {
                    self.skip_bytes(3);
                    self.skip_bytes(64);
                    debug!("LSC_AUTH_CTRL (bitstream is probably signed!)");
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
                    debug!("write {} frames at 0x{:08x}", count, curr_frame);
                    let mut frame_bytes = vec![0 as u8; (bits_per_frame + 14 + 7) / 8];
                    assert_eq!(cfg, 0x91);

                    for _ in 0..count {
                        self.copy_bytes(&mut frame_bytes);
                        self.ecc14 = ECC_INIT;

                        let decoded_frame = chip.frame_addr_to_idx(curr_frame);
                        for j in (0..bits_per_frame).rev() {
                            let ofs = (j + pad_bits) as usize;
                            if ((frame_bytes[(frame_bytes.len() - 1) - (ofs / 8)] >> (ofs % 8))
                                & 0x01)
                                == 0x01
                            {
                                if decoded_frame < chip.cram.frames {
                                    chip.cram.set(decoded_frame, j, true);
                                } else {
                                    debug!("Decoded frame {} exceeds frame size {}", decoded_frame, chip.cram.frames);
                                }
                                if self.verbose {
                                    debug!("F0x{:08x}B{:04}", curr_frame, j);
                                }
                                self.update_ecc(true);
                            } else {
                                self.update_ecc(false);
                            }
                        }
                        let parity = ((frame_bytes[frame_bytes.len() - 2] as u16) << 8
                            | (frame_bytes[frame_bytes.len() - 1] as u16))
                            & 0x3FFF;
                        let exp_parity = self.finalise_ecc();
                        // ECC calculation here is actually occasionally unsound,
                        // as LUT RAM initialisation is masked from ECC calculation
                        // as it changes at runtime. But it is too early to check this here.

                        if self.verbose {
                            debug!("F0x{:08x}P{:014b}E{:014b}", curr_frame, parity, exp_parity);
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
                    debug!("power control: {}", pwr);
                }
                ISC_PROGRAM_USERCODE => {
                    let cmp_crc = self.get_byte() & 0x80 == 0x80;
                    self.skip_bytes(2);
                    let usercode = self.get_u32();
                    debug!("set usercode to 0x{:08X}", usercode);
                    if cmp_crc {
                        self.check_crc16();
                    }
                }
                LSC_BUS_ADDRESS => {
                    self.skip_bytes(3);
                    bus_addr = self.get_u32();
                }
                LSC_BUS_WRITE => {
                    let config = self.get_byte();
                    let cmp_crc = config & 0x80 == 0x80;
                    let frame_count = self.get_u16() as usize;
                    let chip = curr_chip
                        .as_mut()
                        .expect("got bus write without chip setup");
                    let byte_count = frame_count * chip.get_bus_frame_size(bus_addr);
                    for _i in 0..byte_count {
                        chip.ipconfig.insert(bus_addr, self.get_byte());
                        bus_addr += 1;
                    }
                    if cmp_crc {
                        self.check_crc16();
                    }
                }
                LSC_WRITE_COMP_DIC => {
                    self.skip_bytes(3);
                    let mut tmp = [0 as u8; 16];
                    self.copy_bytes(&mut tmp);
                    self.comp_dic = tmp;
                    println!("compression dictionary: {}",
                        self.comp_dic.iter().map(|x| format!("{:02x}", x)).collect::<Vec<_>>().join(" "));
                }
                LSC_PROG_INCR_CMP => {
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
                    println!("write {} compressed frames at 0x{:08x}", count, curr_frame);
                    let mut frame_bytes = vec![0 as u8; 8 * ((bits_per_frame + 14 + 63) / 64)];
                    assert_eq!(cfg, 0xD4);
                    for frame in 0..count {
                        self.decompress_frame(&mut frame_bytes);
                        if self.verbose {
                            println!("decompressed: {}",
                                frame_bytes.iter().map(|x| format!("{:02x}", x)).collect::<Vec<_>>().join(" "));
                        }
                        self.ecc14 = ECC_INIT;
                        for j in (0..bits_per_frame).rev() {
                            let ofs = (j + pad_bits) as usize;
                            if ((frame_bytes[(frame_bytes.len() - 1) - (ofs / 8)] >> (ofs % 8))
                                & 0x01)
                                == 0x01
                            {
                                let decoded_frame = chip.frame_addr_to_idx(curr_frame);
                                if decoded_frame < chip.cram.frames {
                                    chip.cram.set(decoded_frame, j, true);
                                }
                                if self.verbose {
                                    println!("F0x{:08x}B{:04}", curr_frame, j);
                                }
                                self.update_ecc(true);
                            } else {
                                self.update_ecc(false);
                            }
                        }
                        let parity = ((frame_bytes[frame_bytes.len() - 2] as u16) << 8
                            | (frame_bytes[frame_bytes.len() - 1] as u16))
                            & 0x3FFF;
                        let exp_parity = self.finalise_ecc();

                        // ECC calculation here is actually occasionally unsound,
                        // as LUT RAM initialisation is masked from ECC calculation
                        // as it changes at runtime. But it is too early to check this here.

                        if self.verbose {
                            println!("F0x{:08x}P{:014b}E{:014b}", curr_frame, parity, exp_parity);
                        }
                        if frame == count - 1 {
                            self.check_crc16();
                        }
                        for _ in 0..4 {
                            let d = self.get_byte();
                            assert_eq!(d, 0xFF);
                        }
                        curr_frame += 1;
                    }
                }
                ISC_PROGRAM_DONE => {
                    self.skip_bytes(3);
                    debug!("done");
                }
                LSC_READ_DR_UES => {
                    self.skip_bytes(3);
                    debug!("read DR_UES");
                }
                LSC_READ_CNTRL0 => {
                    self.skip_bytes(3);
                    debug!("read CNTRL0");
                }				
                DUMMY => {}
                _ => {
                    warn!("unknown command 0x{:02X} at {}", cmd, self.index);
		    //self.skip_bytes(3);   
                    //return Err("unknown bitstream command");
                }
            }
        }
        match curr_chip {
            Some(x) => Ok(x),
            None => Err("missing bitstream content"),
        }
    }

    fn parse_readback_bistream(&mut self, db: &mut Database) -> Result<Chip, &'static str> {
        // 4 byte IDCODE
        let idcode = self.get_u32();
        let mut chip = Chip::from_idcode(db, idcode);
        // 4 bytes 00 padding
        self.skip_bytes(4);
        // 20 bytes FF padding
        self.skip_bytes(20);
        
        let mut frame_bytes = vec![0 as u8; (chip.data.bits_per_frame + 14 + 7) / 8];
        let mut padding = [0 as u8; 4];

        for i in 0..chip.data.frames {
            let frame_index = if i < 16 {
                // right side IO
                (15 - i) + (16 + chip.tap_frame_count)
            } else if i >= 16 && i < 32 {
                // left side IO
                15 - (i - 16)
            } else if i >= 32 && i < (chip.data.frames - chip.tap_frame_count) {
                // main bitstream
                (chip.data.frames - 1) - (i - 32)
            } else {
                // tap bits
                ((chip.tap_frame_count - 1) - (i - (chip.data.frames - chip.tap_frame_count))) + 16
            };
            // 4 bytes dummy
            self.copy_bytes(&mut padding);
            assert_eq!(padding, [0xFF, 0xFF, 0xFF, 0xFF]);
            // frame data
            self.copy_bytes(&mut frame_bytes);
            for j in 0..(chip.data.bits_per_frame + chip.data.pad_bits_after_frame) {
                // TODO: bit ordering inside frames
                let ofs = (14 + j) as usize;
                let val = ((frame_bytes[(frame_bytes.len() - 1) - (ofs / 8)] >> (ofs % 8)) & 0x01) == 0x01;
                if j < chip.data.bits_per_frame {
                    if val {
                        chip.cram.set(frame_index, j, true);
                    }
                } else {
                    // padding bit, should be one
                    assert!(val);
                }
            }
        }
        Ok(chip)
    }

    pub fn parse(&mut self, db: &mut Database) -> Result<Chip, &'static str> {
        let typ = self.parse_container()?;
        let c = match typ {
            BitstreamType::NORMAL => self.parse_bitstream(db)?,
            BitstreamType::READBACK => self.parse_readback_bistream(db)?,
        };
        Ok(c)
    }
}
