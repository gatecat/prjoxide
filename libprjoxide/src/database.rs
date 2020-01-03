use ron::ser::PrettyConfig;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fmt;
use std::fs::File;
use std::io::prelude::*;
use std::ops::Not;
use std::path::Path;
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

// Deserialization of 'baseaddr.json'

#[derive(Deserialize)]
pub struct DeviceBaseAddrs {
    pub regions: BTreeMap<String, DeviceBaseAddrs>,
}

#[derive(Deserialize)]
pub struct DeviceAddrRegion {
    pub addr: u32,
    pub abits: u32
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
    pub bits: Vec<BTreeSet<ConfigBit>>,
    #[serde(default)]
    #[serde(skip_serializing_if = "String::is_empty")]
    pub desc: String,
}

#[derive(Deserialize, Serialize, Clone)]
pub struct ConfigEnumData {
    pub options: BTreeMap<String, BTreeSet<ConfigBit>>,
    #[serde(default)]
    #[serde(skip_serializing_if = "String::is_empty")]
    pub desc: String,
}

fn is_false(x: &bool) -> bool {
    !(*x)
}

#[derive(Deserialize, Serialize, Clone)]
pub struct FixedConnectionData {
    pub from_wire: String,
    #[serde(default)]
    #[serde(skip_serializing_if = "is_false")]
    pub bidir: bool,
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
    pub fn add_word(&mut self, name: &str, desc: &str, bits: Vec<BTreeSet<ConfigBit>>) {
        self.dirty = true;
        match self.db.words.get_mut(name) {
            None => {
                self.db.words.insert(
                    name.to_string(),
                    ConfigWordData {
                        desc: desc.to_string(),
                        bits: bits.clone(),
                    },
                );
            }
            Some(word) => {
                if !desc.is_empty() && desc != &word.desc {
                    word.desc = desc.to_string();
                }
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
    pub fn add_enum_option(
        &mut self,
        name: &str,
        option: &str,
        desc: &str,
        bits: BTreeSet<ConfigBit>,
    ) {
        if !self.db.enums.contains_key(name) {
            self.db.enums.insert(
                name.to_string(),
                ConfigEnumData {
                    options: BTreeMap::new(),
                    desc: desc.to_string(),
                },
            );
        }
        let ec = self.db.enums.get_mut(name).unwrap();
        if !desc.is_empty() && desc != &ec.desc {
            ec.desc = desc.to_string();
            self.dirty = true;
        }
        match ec.options.get(option) {
            Some(old_bits) => {
                if bits != *old_bits {
                    panic!(
                        "Bit conflict for {}.{}={} existing: {:?} new: {:?}",
                        self.tiletype, name, option, old_bits, bits
                    );
                }
            }
            None => {
                ec.options.insert(option.to_string(), bits);
                self.dirty = true;
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
                bidir: false,
            });
        }
    }
}

pub struct Database {
    root: String,
    devices: DevicesDatabase,
    tilegrids: HashMap<(String, String), DeviceTilegrid>,
    baseaddrs: HashMap<(String, String), DeviceBaseAddrs>,
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
            baseaddrs: HashMap::new(),
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
    // IP region base addresses for a device by family and name
    pub fn device_baseaddrs(&mut self, family: &str, device: &str) -> &DeviceBaseAddrs {
        let key = (family.to_string(), device.to_string());
        if !self.baseaddrs.contains_key(&key) {
            let mut bs_json_buf = String::new();
            // read the whole file
            File::open(format!("{}/{}/{}/baseaddrs.json", self.root, family, device))
                .unwrap()
                .read_to_string(&mut bs_json_buf)
                .unwrap();
            let bs = serde_json::from_str(&bs_json_buf).unwrap();
            self.baseaddrs.insert(key.clone(), bs);
        }
        self.baseaddrs.get(&key).unwrap()
    }
    // Bit database for a tile by family and tile type
    pub fn tile_bitdb(&mut self, family: &str, tiletype: &str) -> &mut TileBitsData {
        let key = (family.to_string(), tiletype.to_string());
        if !self.tilebits.contains_key(&key) {
            // read the whole file
            let filename = format!("{}/{}/tiletypes/{}.ron", self.root, family, tiletype);
            let tb = if Path::new(&filename).exists() {
                let mut tt_ron_buf = String::new();
                File::open(filename)
                    .unwrap()
                    .read_to_string(&mut tt_ron_buf)
                    .unwrap();
                ron::de::from_str(&tt_ron_buf).unwrap()
            } else {
                TileBitsDatabase {
                    pips: BTreeMap::new(),
                    words: BTreeMap::new(),
                    enums: BTreeMap::new(),
                    conns: BTreeMap::new(),
                }
            };
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
            let pretty = PrettyConfig {
                depth_limit: 5,
                new_line: "\n".to_string(),
                indentor: "  ".to_string(),
                enumerate_arrays: false,
                separate_tuple_members: false,
            };
            let tt_ron_buf = ron::ser::to_string_pretty(&tilebits.db, pretty).unwrap();
            File::create(format!(
                "{}/{}/tiletypes/{}.ron",
                self.root, family, tiletype
            ))
            .unwrap()
            .write_all(tt_ron_buf.as_bytes())
            .unwrap();
            tilebits.dirty = false;
        }
    }
}
