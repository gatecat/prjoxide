use crate::database::*;
use multimap::MultiMap;
use std::collections::HashMap;

// 2D bit array
pub struct BitMatrix {
    frames: usize,
    bits: usize,
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
                let f = i / self.frames;
                let b = i % self.frames;
                match (o, n) {
                    (false, true) => Some((f, b, true)),  // going high
                    (true, false) => Some((f, b, false)), // going low
                    _ => None,
                }
            })
            .collect()
    }
}

struct Chip {
    // Family name
    family: String,
    // Device name
    device: String,
    // Device data
    data: DeviceData,
    // Entire main bitstream content
    cram: BitMatrix,
    // All of the tiles in the chip
    tiles: Vec<Tile>,
    // IP core and EBR configuration
    ipconfig: HashMap<u32, u32>,
    // Fast references to tiles
    tiles_by_name: HashMap<String, usize>,
    tiles_by_loc: MultiMap<(u32, u32), usize>,
    // Metadata (comment strings in bitstream)
    metadata: Vec<String>,
}

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
                .map(|(name, data)| Tile::new(name, data))
                .collect(),
            ipconfig: HashMap::new(),
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
}

// Actual instance of a tile
pub struct Tile {
    pub name: String,
    pub tiletype: String,
    pub x: u32,
    pub y: u32,
    pub start_bit: usize,
    pub start_frame: usize,
    pub cram: BitMatrix,
}

impl Tile {
    pub fn new(name: &str, data: &TileData) -> Tile {
        Tile {
            name: name.to_string(),
            tiletype: data.tiletype.to_string(),
            x: 0, // FIXME
            y: 0,
            start_bit: data.start_bit,
            start_frame: data.start_frame,
            cram: BitMatrix::new(data.frames, data.bits),
        }
    }
}
