use crate::database::*;
use std::collections::HashMap;

// 2D bit array
struct BitMatrix {
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
    // Create a bitmatrix as a window of a larger one
    pub fn from_window(
        base: &Self,
        start_frame: usize,
        start_bit: usize,
        frames: usize,
        bits: usize,
    ) -> BitMatrix {
        let mut m = BitMatrix {
            frames: frames,
            bits: bits,
            data: vec![false; frames * bits],
        };

        for f in 0..frames {
            for b in 0..bits {
                m.data[f * bits + b] = base.data[(f + start_frame) * base.bits + (b + start_bit)];
            }
        }

        m
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
    tiles_by_loc: HashMap<(u32, u32), usize>,
    // Metadata (comment strings in bitstream)
    metadata: Vec<String>,
}

// Actual instance of a tile
struct Tile {
    name: String,
    tiletype: String,
    x: u32,
    y: u32,
    start_bit: usize,
    start_frame: usize,
    cram: BitMatrix,
}

// The differences between two chips
