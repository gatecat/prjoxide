use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fmt;
use std::fs::File;
use std::io::prelude::*;
// Deserialization of 'devices.json'

#[derive(Deserialize)]
pub struct DevicesDatabase {
    pub families: BTreeMap<String, FamilyData>,
}

#[derive(Deserialize)]
pub struct FamilyData {
    pub devices: BTreeMap<String, DeviceData>,
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
    pub tiles: BTreeMap<String, TileData>,
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

impl fmt::Debug for ConfigBit {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "{}F{}B{}",
            match self.invert {
                true => "!",
                false => "",
            },
            self.frame,
            self.bit
        )
    }
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ConfigPipData {
    pub from_wire: String,
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
    pub from_wire: String,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct TileBitsDatabase {
    pub pips: BTreeMap<String, Vec<ConfigPipData>>,
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
    pub fn new(tiletype: &str, db: TileBitsDatabase) -> TileBitsData {
        TileBitsData {
            tiletype: tiletype.to_string(),
            db: db.clone(),
            dirty: false,
        }
    }
    pub fn add_pip(&mut self, from: &str, to: &str, bits: BTreeSet<ConfigBit>) {
        if !self.db.pips.contains_key(to) {
            self.db.pips.insert(to.to_string(), Vec::new());
        }
        let ac = self.db.pips.get_mut(to).unwrap();
        for ad in ac.iter() {
            if ad.from_wire == from {
                if bits != ad.bits {
                    panic!(
                        "Bit conflict for {}.{}<-{} existing: {:?} new: {:?}",
                        self.tiletype, from, to, ad.bits, bits
                    );
                }
                return;
            }
        }
        self.dirty = true;
        ac.push(ConfigPipData {
            from_wire: from.to_string(),
            bits: bits.clone(),
        });
    }
    pub fn add_word(&mut self, name: &str, defval: Vec<bool>, bits: Vec<BTreeSet<ConfigBit>>) {
        self.dirty = true;
        match self.db.words.get(name) {
            None => {
                self.db.words.insert(
                    name.to_string(),
                    ConfigWordData {
                        defval: defval,
                        bits: bits.clone(),
                    },
                );
            }
            Some(word) => {
                if bits.len() != word.bits.len() {
                    panic!(
                        "Width conflict {}.{} existing: {:?} new: {:?}",
                        self.tiletype,
                        name,
                        word.bits.len(),
                        bits.len()
                    );
                }
                for (bit, (e, n)) in word.bits.iter().zip(bits.iter()).enumerate() {
                    if e != n {
                        panic!(
                            "Bit conflict for {}.{}[{}] existing: {:?} new: {:?}",
                            self.tiletype, name, bit, e, n
                        );
                    }
                }
            }
        }
    }
    pub fn add_conn(&mut self, from: &str, to: &str) {
        if !self.db.conns.contains_key(to) {
            self.db.conns.insert(to.to_string(), Vec::new());
        }
        let pc = self.db.conns.get_mut(to).unwrap();
        if pc.iter().any(|fc| fc.from_wire == from) {
            // Connection already exists
        } else {
            self.dirty = true;
            pc.push(FixedConnectionData {
                from_wire: from.to_string(),
            });
        }
    }
}

pub struct Database {
    root: String,
    devices: DevicesDatabase,
    tilegrids: HashMap<(String, String), DeviceTilegrid>,
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
    // Both functions return a (family, name, data) 3-tuple
    pub fn device_by_name(&self, name: &str) -> Option<(String, String, DeviceData)> {
        for (f, fd) in self.devices.families.iter() {
            for (d, data) in fd.devices.iter() {
                if d == name {
                    return Some((f.to_string(), d.to_string(), data.clone()));
                }
            }
        }
        None
    }
    pub fn device_by_idcode(&self, idcode: u32) -> Option<(String, String, DeviceData)> {
        for (f, fd) in self.devices.families.iter() {
            for (d, data) in fd.devices.iter() {
                if data.idcode == idcode {
                    return Some((f.to_string(), d.to_string(), data.clone()));
                }
            }
        }
        None
    }
    // Tilegrid for a device by family and name
    pub fn device_tilegrid(&mut self, family: &str, device: &str) -> &DeviceTilegrid {
        let key = (family.to_string(), device.to_string());
        if !self.tilegrids.contains_key(&key) {
            let mut tg_json_buf = String::new();
            // read the whole file
            File::open(format!("{}/{}/{}/tilegrid.json", self.root, family, device))
                .unwrap()
                .read_to_string(&mut tg_json_buf)
                .unwrap();
            let tg = serde_json::from_str(&tg_json_buf).unwrap();
            self.tilegrids.insert(key.clone(), tg);
        }
        self.tilegrids.get(&key).unwrap()
    }
    // Bit database for a tile by family and tile type
    pub fn tile_bitdb(&mut self, family: &str, tiletype: &str) -> &mut TileBitsData {
        let key = (family.to_string(), tiletype.to_string());
        if !self.tilebits.contains_key(&key) {
            let mut tt_json_buf = String::new();
            // read the whole file
            File::open(format!(
                "{}/{}/tiletypes/{}.json",
                self.root, family, tiletype
            ))
            .unwrap()
            .read_to_string(&mut tt_json_buf)
            .unwrap();
            let tb = serde_json::from_str(&tt_json_buf).unwrap();
            self.tilebits
                .insert(key.clone(), TileBitsData::new(tiletype.clone(), tb));
        }
        self.tilebits.get_mut(&key).unwrap()
    }
    // Flush tile bit database changes to disk
    pub fn flush(&mut self) {
        for kv in self.tilebits.iter_mut() {
            let (family, tiletype) = kv.0;
            let tilebits = kv.1;
            if !tilebits.dirty {
                continue;
            }
            let tt_json_buf = serde_json::to_vec(&tilebits.db).unwrap();
            File::create(format!(
                "{}/{}/tiletypes/{}.json",
                self.root, family, tiletype
            ))
            .unwrap()
            .write_all(&tt_json_buf)
            .unwrap();
            tilebits.dirty = false;
        }
    }
}
