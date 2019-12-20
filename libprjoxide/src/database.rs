use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::File;
use std::io;
use std::io::prelude::*;
// Deserialization of 'devices.json'

#[derive(Deserialize)]
pub struct DevicesDatabase {
    pub families: HashMap<String, FamilyData>,
}

#[derive(Deserialize)]
pub struct FamilyData {
    pub devices: HashMap<String, DeviceData>,
}

#[derive(Deserialize, Clone)]
pub struct DeviceData {
    pub packages: Vec<String>,
    pub idcode: u32,
    pub frames: usize,
    pub bits_per_frame: usize,
    pub pad_bits_after_frame: usize,
    pub pad_bits_before_frame: usize,
    pub frame_ecc_bits: usize,
    pub max_row: u32,
    pub max_col: u32,
    pub col_bias: u32,
    pub fuzz: bool,
}

// Deserialization of 'tilegrid.json'

#[derive(Deserialize)]
pub struct DeviceTilegrid {
    pub tiles: HashMap<String, TileData>,
}

#[derive(Deserialize)]
pub struct TileData {
    pub tiletype: String,
    pub x: u32,
    pub y: u32,
    pub start_bit: usize,
    pub start_frame: usize,
    pub bits: usize,
    pub frames: usize,
}

// Tile bit database structures

#[derive(Deserialize, Serialize, PartialEq, Eq, PartialOrd, Ord, Clone)]
pub struct ConfigBit {
    pub frame: usize,
    pub bit: usize,
    pub invert: bool,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ConfigArcData {
    pub to_wire: String,
    pub bits: BTreeSet<ConfigBit>,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ConfigWordData {
    pub defval: Vec<bool>,
    pub bits: Vec<BTreeSet<ConfigBit>>,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ConfigEnumData {
    pub defval: String,
    pub bits: BTreeMap<String, BTreeSet<ConfigBit>>,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct FixedConnectionData {
    pub to_wire: String,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct TileBitsDatabase {
    pub arcs: BTreeMap<String, Vec<ConfigArcData>>,
    pub words: BTreeMap<String, ConfigWordData>,
    pub enums: BTreeMap<String, ConfigEnumData>,
    pub conns: BTreeMap<String, Vec<FixedConnectionData>>,
}

pub struct TileBitsData {
    tiletype: String,
    pub db: TileBitsDatabase,
    dirty: bool,
}

impl TileBitsData {
    pub fn new(tiletype: &str, db: &TileBitsDatabase) -> TileBitsData {
        TileBitsData {
            tiletype: tiletype.to_string(),
            db: db.clone(),
            dirty: false,
        }
    }
    pub fn add_arc(&mut self, from: &str, to: &str, bits: ConfigBit) {}
}

pub struct Database {
    root: String,
    devices: DevicesDatabase,
    tilegrids: HashMap<String, DeviceTilegrid>,
    tilebits: HashMap<(String, String), TileBitsData>,
}

impl Database {
    pub fn new(root: &str) -> Database {
        let mut devices_json_buf = String::new();
        // read the whole file
        File::open(format!("{}/devices.json", root))
            .unwrap()
            .read_to_string(&mut devices_json_buf)
            .unwrap();
        Database {
            root: root.to_string(),
            devices: serde_json::from_str(&devices_json_buf).unwrap(),
            tilegrids: HashMap::new(),
            tilebits: HashMap::new(),
        }
    }
}
