use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};

// Deserialization of 'devices.json'

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
    max_row: u32,
    max_col: u32,
    col_bias: u32,
    fuzz: bool,
}

// Deserialization of 'tilegrid.json'

#[derive(Deserialize)]
struct DeviceTilegrid {
    tiles: HashMap<String, TileData>,
}

#[derive(Deserialize)]
struct TileData {
    tiletype: String,
    start_bit: usize,
    start_frame: usize,
    bits: usize,
    frames: usize,
}

// Tile bit database structures

#[derive(Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord)]
struct ConfigBit {
    frame: usize,
    bit: usize,
    invert: bool,
}

#[derive(Deserialize, Serialize)]
struct ConfigArcData {
    from_wire: String,
    to_wire: String,
    bits: BTreeSet<ConfigBit>,
}

#[derive(Deserialize, Serialize)]
struct ConfigWordData {
    defval: Vec<bool>,
    bits: Vec<BTreeSet<ConfigBit>>,
}

#[derive(Deserialize, Serialize)]
struct ConfigEnumData {
    defval: String,
    bits: BTreeMap<String, BTreeSet<ConfigBit>>,
}

#[derive(Deserialize, Serialize)]
struct FixedConnectionData {
    from_wire: String,
    to_wire: String,
}

#[derive(Deserialize, Serialize)]
struct TileBitsDatabase {
    arcs: Vec<ConfigArcData>,
    words: Vec<ConfigWordData>,
    enums: Vec<ConfigEnumData>,
    conns: Vec<FixedConnectionData>,
}
