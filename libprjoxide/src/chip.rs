use crate::database::*;
use crate::fasmparse::*;
use multimap::MultiMap;
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::io::Write;

// 2D bit array
#[derive(Clone)]
pub struct BitMatrix {
    pub frames: usize,
    pub bits: usize,
    data: Vec<bool>,
}

impl BitMatrix {
    // Create new empty bitmatrix
    pub fn new(frames: usize, bits: usize) -> BitMatrix {
        BitMatrix {
            frames: frames,
            bits: bits,
            data: vec![false; frames * bits],
        }
    }
    // Getting and setting bits
    pub fn get(&self, frame: usize, bit: usize) -> bool {
        self.data[frame * self.bits + bit]
    }
    pub fn set(&mut self, frame: usize, bit: usize, val: bool) {
        self.data[frame * self.bits + bit] = val
    }
    // Copy another bitmatrix to a window of this one
    pub fn copy_window(&mut self, from: &Self, start_frame: usize, start_bit: usize) {
        for f in 0..from.frames {
            for b in 0..from.bits {
                self.data[(f + start_frame) * self.bits + (b + start_bit)] =
                    from.data[f * from.bits + b];
            }
        }
    }
    // Copy a window another bitmatrix  to this one
    pub fn copy_from_window(&mut self, from: &Self, start_frame: usize, start_bit: usize) {
        for f in 0..self.frames {
            for b in 0..self.bits {
                self.data[f * self.bits + b] =
                    from.data[(f + start_frame) * from.bits + (b + start_bit)];
            }
        }
    }
    // Get a list of the differences
    // as a tuple (frame, bit, new value)
    pub fn delta(&self, base: &Self) -> Vec<(usize, usize, bool)> {
        base.data
            .iter()
            .zip(self.data.iter())
            .enumerate()
            .filter_map(|(i, (o, n))| {
                let f = i / self.bits;
                let b = i % self.bits;
                match (o, n) {
                    (false, true) => Some((f, b, true)),  // going high
                    (true, false) => Some((f, b, false)), // going low
                    _ => None,
                }
            })
            .collect()
    }
    // Pretty-print a list of frame-bits
    pub fn print(&self, mut out: &mut dyn Write) {
        for (i, _x) in self.data.iter().enumerate().filter(|(_i, x)| **x) {
            let f = i / self.bits;
            let b = i % self.bits;
            writeln!(&mut out, "F{}B{}", f, b).unwrap();
        }
    }
    // Return true if any bit is set
    pub fn any(&self) -> bool {
        return self.data.iter().any(|x| *x);
    }
}

#[derive(Clone)]
pub struct Chip {
    // Family name
    pub family: String,
    // Device name
    pub device: String,
    // Device data
    pub data: DeviceData,
    // Entire main bitstream content
    pub cram: BitMatrix,
    // All of the tiles in the chip
    pub tiles: Vec<Tile>,
    // IP core and EBR configuration
    pub ipconfig: BTreeMap<u32, u8>,
    // Fast references to tiles
    tiles_by_name: HashMap<String, usize>,
    tiles_by_loc: MultiMap<(u32, u32), usize>,
    // Metadata (comment strings in bitstream)
    pub metadata: Vec<String>,
}

pub type ChipDelta = BTreeMap<String, Vec<(usize, usize, bool)>>;

impl Chip {
    pub fn new(family: &str, device: &str, data: &DeviceData, tiles: &DeviceTilegrid) -> Chip {
        let mut c = Chip {
            family: family.to_string(),
            device: device.to_string(),
            data: data.clone(),
            cram: BitMatrix::new(data.frames, data.bits_per_frame),
            tiles: tiles
                .tiles
                .iter()
                .map(|(name, data)| Tile::new(name, family, data))
                .collect(),
            ipconfig: BTreeMap::new(),
            tiles_by_name: HashMap::new(),
            tiles_by_loc: MultiMap::new(),
            metadata: Vec::new(),
        };
        c.tiles_by_name = c
            .tiles
            .iter()
            .enumerate()
            .map(|(i, t)| (t.name.to_string(), i))
            .collect();
        c.tiles_by_loc = c
            .tiles
            .iter()
            .enumerate()
            .map(|(i, t)| ((t.x, t.y), i))
            .collect();
        c
    }
    // Create a new chip from the database based on IDCODE or name
    pub fn from_idcode(db: &mut Database, idcode: u32) -> Chip {
        let (fam, device, data) = db.device_by_idcode(idcode).expect(&format!(
            "no device in database with IDCODE {:08x}\n",
            idcode
        ));
        Chip::new(&fam, &device, &data, db.device_tilegrid(&fam, &device))
    }
    pub fn from_name(db: &mut Database, name: &str) -> Chip {
        let (fam, device, data) = db
            .device_by_name(name)
            .expect(&format!("no device in database with name {}\n", name));
        Chip::new(&fam, &device, &data, db.device_tilegrid(&fam, &device))
    }
    pub fn from_fasm(db: &mut Database, fasm: &ParsedFasm, device: Option<&str>) -> Chip {
        let mut chip = match device {
            Some(d) => Chip::from_name(db, d),
            None => {
                let name = &fasm
                    .attrs
                    .iter()
                    .find(|(k, _)| k == "oxide.device")
                    .unwrap()
                    .1;
                Chip::from_name(db, name)
            }
        };
        chip.metadata.extend(
            fasm.attrs
                .iter()
                .filter_map(|(k, v)| if k == "oxide.meta" { Some(v) } else { None })
                .cloned(),
        );
        for (tn, ft) in fasm.tiles.iter() {
            chip.tile_by_name_mut(tn).unwrap().from_fasm(db, ft);
        }
        chip.tiles_to_cram();
        return chip;
    }
    // Copy the whole-chip CRAM to the per-tile CRAM
    pub fn cram_to_tiles(&mut self) {
        for t in self.tiles.iter_mut() {
            t.cram
                .copy_from_window(&self.cram, t.start_frame, t.start_bit);
        }
    }
    // Copy the per-tile CRAM windows to the whole chip CRAM
    pub fn tiles_to_cram(&mut self) {
        for t in self.tiles.iter() {
            self.cram.copy_window(&t.cram, t.start_frame, t.start_bit);
        }
    }
    // Get a tile by name
    pub fn tile_by_name(&self, name: &str) -> Result<&Tile, &'static str> {
        match self.tiles_by_name.get(name) {
            None => {
                println!("no tile named {}", name);
                Err("unknown tile name")
            }
            Some(i) => Ok(&self.tiles[*i]),
        }
    }
    // Get a mutable tile by name
    pub fn tile_by_name_mut(&mut self, name: &str) -> Result<&mut Tile, &'static str> {
        match self.tiles_by_name.get(name) {
            None => {
                println!("no tile named {}", name);
                Err("unknown tile name")
            }
            Some(i) => Ok(&mut self.tiles[*i]),
        }
    }
    // Get all tiles at a location
    pub fn tiles_by_xy(&self, x: u32, y: u32) -> Vec<&Tile> {
        match self.tiles_by_loc.get_vec(&(x, y)) {
            None => Vec::new(),
            Some(v) => v.iter().map(|i| &self.tiles[*i]).collect(),
        }
    }
    // Compare two chips
    pub fn delta(&self, base: &Self) -> ChipDelta {
        base.tiles
            .iter()
            .zip(self.tiles.iter())
            .map(|(t1, t2)| {
                assert_eq!(t1.name, t2.name);
                (t1.name.to_string(), t2.cram.delta(&t1.cram))
            })
            .filter(|(_k, v)| v.len() > 0)
            .collect()
    }
    // Dump chip to a simple text format for debugging
    pub fn print(&self, mut out: &mut dyn Write) {
        writeln!(&mut out, ".device {}", self.device).unwrap();
        for m in self.metadata.iter() {
            writeln!(&mut out, ".metadata {}", m).unwrap();
        }
        for t in self.tiles.iter() {
            t.print(&mut out);
        }
        for (addr, data) in self.ipconfig.iter() {
            writeln!(&mut out, ".write 0x{:08x} 0x{:08x}", addr, data).unwrap();
        }
    }
    // Convert frame address to flat frame index
    pub fn frame_addr_to_idx(&self, addr: u32) -> usize {
        match addr {
            0x0000..=0x7FFF => (self.cram.frames - 1) - (addr as usize),
            0x8000..=0x800F => (15 - ((addr - 0x8000) as usize)) + 40, // right side IO
            0x8010..=0x801F => (15 - ((addr - 0x8010) as usize)) + 0,  // left side IO
            0x8020..=0x8037 => (23 - ((addr - 0x8020) as usize)) + 16, // TAPs (row-segment clocking)
            _ => panic!("unable to process frame address 0x{:08x}", addr),
        }
    }
    // Get the frame size in bytes for bus regions
    pub fn get_bus_frame_size(&self, addr: u32) -> usize {
        match (addr & 0xF0000000) >> 28 {
            0 => 1, // non-PCIe IP cores
            2 => 5, // BRAM and LRAM
            3 => 4, // PCIe IP
            _ => panic!(
                "unable to determine frame size of bus address 0x{:08x}",
                addr
            ),
        }
    }
}

// Actual instance of a tile
#[derive(Clone)]
pub struct Tile {
    pub name: String,
    pub family: String,
    pub tiletype: String,
    pub x: u32,
    pub y: u32,
    pub start_bit: usize,
    pub start_frame: usize,
    pub cram: BitMatrix,
}

impl Tile {
    pub fn new(name: &str, family: &str, data: &TileData) -> Tile {
        Tile {
            name: name.to_string(),
            family: family.to_string(),
            tiletype: data.tiletype.to_string(),
            x: data.x,
            y: data.y,
            start_bit: data.start_bit,
            start_frame: data.start_frame,
            cram: BitMatrix::new(data.frames, data.bits),
        }
    }
    pub fn print(&self, mut out: &mut dyn Write) {
        if self.cram.any() {
            writeln!(&mut out, ".tile {}:{}", self.name, self.tiletype).unwrap();
            self.cram.print(&mut out);
        }
    }
    pub fn from_fasm(&mut self, db: &mut Database, ft: &FasmTile) {
        let tdb = db.tile_bitdb(&self.family, &self.tiletype);
        for i in 0..2 {
            // Process "BASE_" enums first
            for (k, v) in ft
                .enums
                .iter()
                .filter(|(k, _)| k.starts_with("BASE_") == (i == 0) && !k.starts_with("UNKNOWN."))
            {
                let en = tdb.db.enums.get(k).unwrap_or_else(|| panic!("No enum named {} in tile {}.\n\
Please make sure Oxide and nextpnr are up to date. If they are, consider reporting this as an issue.", k, self.name));
                let opt = en.options.get(v).unwrap_or_else(|| panic!("No option named {} for enum {} in tile {}.\n\
Valid options are: {}\n\
Please make sure Oxide and nextpnr are up to date and input source code is meaningful. If they are, consider reporting this as an issue.",
                            v, k, self.name,
                            en.options.keys().cloned().collect::<Vec<String>>().join(", ")));
                for bit in opt.iter() {
                    self.cram.set(bit.frame, bit.bit, !bit.invert);
                }
            }
        }
        // Process words
        for (k, v) in ft.words.iter() {
            let w = tdb.db.words.get(k).unwrap_or_else(|| panic!("No word named {} in tile {}.\n\
Please make sure Oxide and nextpnr are up to date. If they are, consider reporting this as an issue.", k, self.name));
            if (v.significant_bits() as usize) > w.bits.len() {
                panic!(
                    "Word {} in tile {} has value width {} exceeding database width of {}",
                    k,
                    self.name,
                    v.significant_bits(),
                    w.bits.len()
                );
            }
            for (i, wb) in w.bits.iter().enumerate() {
                let bit_val = v.get_bit(i as u32);
                for bit in wb {
                    self.cram.set(bit.frame, bit.bit, bit.invert != bit_val);
                }
            }
        }
        // Process pips
        for (tw, fw) in ft.pips.iter() {
            let found_pip = tdb
                .db
                .pips
                .get(tw)
                .map_or(None, |pips| pips.iter().find(|p| &p.from_wire == fw));
            match found_pip {
                Some(p) => {
                    for bit in p.bits.iter() {
                        self.cram.set(bit.frame, bit.bit, !bit.invert);
                    }
                }
                None => {
                    // Panic iff fixed connection doesn't exist
                    let found_fc = tdb
                        .db
                        .conns
                        .get(tw)
                        .map_or(None, |conns| conns.iter().find(|c| &c.from_wire == fw));
                    if found_fc.is_none() {
                        panic!("No pip {}.{} in tile {}.\n\
Please make sure Oxide and nextpnr are up to date. If they are, consider reporting this as an issue.", fw, tw, self.name);
                    }
                }
            }
        }
        // Process unknowns
        for (f, b) in ft.unknowns.iter() {
            self.cram.set(*f, *b, true);
        }
    }
    pub fn write_fasm(&self, db: &mut Database, mut out: &mut dyn Write) {
        let tdb = db.tile_bitdb(&self.family, &self.tiletype);
        let fasm_name = self.name.replace(':', "__");
        let mut known_bits = BTreeSet::<(usize, usize)>::new();
        let mut total_matches = 0;
        for (to_wire, pips) in tdb.db.pips.iter() {
            let best_match = pips
                .iter()
                .filter(|p| {
                    p.bits.iter().any(|cb| !cb.invert)
                        && p.bits
                            .iter()
                            .all(|cb| self.cram.get(cb.frame, cb.bit) == !cb.invert)
                })
                .max_by_key(|p| p.bits.len());
            if let Some(m) = best_match {
                writeln!(
                    &mut out,
                    "{}.PIP.{}.{}",
                    fasm_name,
                    to_wire.replace(':', "__"),
                    m.from_wire.replace(':', "__")
                )
                .unwrap();
                let mut matched_bits = m.bits.iter().map(|cb| (cb.frame, cb.bit)).collect();
                known_bits.append(&mut matched_bits);
                total_matches += 1;
            }
        }
        for (name, edata) in tdb.db.enums.iter() {
            let best_match = edata
                .options
                .iter()
                .filter(|(_k, v)| {
                    v.iter().any(|cb| !cb.invert)
                        && v.iter()
                            .all(|cb| self.cram.get(cb.frame, cb.bit) == !cb.invert)
                })
                .max_by_key(|(_k, v)| v.len());
            if let Some((opt, bits)) = best_match {
                writeln!(&mut out, "{}.{}.{}", fasm_name, name, opt).unwrap();
                let mut matched_bits = bits.iter().map(|cb| (cb.frame, cb.bit)).collect();
                known_bits.append(&mut matched_bits);
                total_matches += 1;
            }
        }
        for (name, wdata) in tdb.db.words.iter() {
            // Skip words with no set bits
            if !wdata
                .bits
                .iter()
                .flatten()
                .any(|cb| self.cram.get(cb.frame, cb.bit))
            {
                continue;
            }
            let bitstr: String = wdata
                .bits
                .iter()
                .rev()
                .map(|b| {
                    match b
                        .iter()
                        .all(|cb| self.cram.get(cb.frame, cb.bit) == !cb.invert)
                    {
                        true => '1',
                        false => '0',
                    }
                })
                .collect();
            writeln!(
                &mut out,
                "{}.{}[{}:0] = {}'b{}",
                fasm_name,
                name,
                wdata.bits.len() - 1,
                wdata.bits.len(),
                bitstr
            )
            .unwrap();
            let mut matched_bits = wdata
                .bits
                .iter()
                .flatten()
                .map(|cb| (cb.frame, cb.bit))
                .collect();
            known_bits.append(&mut matched_bits);
            total_matches += 1;
        }
        for f in 0..self.cram.frames {
            for b in 0..self.cram.bits {
                if self.cram.get(f, b) && !known_bits.contains(&(f, b)) {
                    writeln!(&mut out, "{}.UNKNOWN.{}.{}", fasm_name, f, b).unwrap();
                    total_matches += 1;
                }
            }
        }
        if total_matches > 0 {
            writeln!(&mut out, "").unwrap();
        }
    }
}
