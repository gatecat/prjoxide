use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize)]
struct DevicesDatabase {
    families: HashMap<String, FamilyData>,
}

#[derive(Deserialize)]
struct FamilyData {
    devices: HashMap<String, DeviceData>,
}

#[derive(Deserialize)]
struct DeviceData {
    packages: Vec<String>,
    idcode: u32,
    frames: usize,
    bits_per_frame: usize,
    pad_bits_after_frame: usize,
    pad_bits_before_frame: usize,
    frame_ecc_bits: usize,
    max_row: usize,
    max_col: usize,
    col_bias: usize,
    fuzz: bool,
}
