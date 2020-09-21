use crate::bitstream::*;
use crate::chip::*;
use crate::database::*;
use std::collections::{BTreeMap, BTreeSet};
use std::iter::FromIterator;

pub enum IPFuzzMode {
    Word { name: String, width: usize },
    Enum { name: String },
}

#[derive(PartialEq, Eq, PartialOrd, Ord, Clone)]
enum IPFuzzKey {
    WordKey { bits: Vec<bool> },
    EnumKey { option: String },
}

pub struct IPFuzzer {
    mode: IPFuzzMode,
    ipcore: String,
    iptype: String,
    base: Chip,                           // bitstream with nothing set
    deltas: BTreeMap<IPFuzzKey, IPDelta>, // used for words and enums
    desc: String,                         // description of the setting being fuzzed
}

impl IPFuzzer {
    pub fn init_word_fuzzer(
        _db: &mut Database,
        base_bit: &Chip,
        fuzz_ipcore: &str,
        fuzz_iptype: &str,
        name: &str,
        desc: &str,
        width: usize,
    ) -> IPFuzzer {
        IPFuzzer {
            mode: IPFuzzMode::Word {
                name: name.to_string(),
                width: width,
            },
            ipcore: fuzz_ipcore.to_string(),
            iptype: fuzz_iptype.to_string(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
            desc: desc.to_string(),
        }
    }
    pub fn init_enum_fuzzer(
        base_bit: &Chip,
        fuzz_ipcore: &str,
        fuzz_iptype: &str,
        name: &str,
        desc: &str,
    ) -> IPFuzzer {
        IPFuzzer {
            mode: IPFuzzMode::Enum {
                name: name.to_string(),
            },
            ipcore: fuzz_ipcore.to_string(),
            iptype: fuzz_iptype.to_string(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
            desc: desc.to_string(),
        }
    }
    fn add_sample(&mut self, db: &mut Database, key: IPFuzzKey, bitfile: &str) {
        let parsed_bitstream = BitstreamParser::parse_file(db, bitfile).unwrap();
        let addr = db
            .device_baseaddrs(&parsed_bitstream.family, &parsed_bitstream.device)
            .regions
            .get(&self.ipcore)
            .unwrap();
        let delta: IPDelta =
            parsed_bitstream.ip_delta(&self.base, addr.addr, addr.addr + (1 << addr.abits));
        self.deltas.insert(key, delta);
    }
    pub fn add_word_sample(&mut self, db: &mut Database, set_bits: Vec<bool>, bitfile: &str) {
        self.add_sample(db, IPFuzzKey::WordKey { bits: set_bits }, bitfile);
    }
    pub fn add_enum_sample(&mut self, db: &mut Database, option: &str, bitfile: &str) {
        self.add_sample(
            db,
            IPFuzzKey::EnumKey {
                option: option.to_string(),
            },
            bitfile,
        );
    }
    pub fn solve(&mut self, db: &mut Database) {
        match &self.mode {
            IPFuzzMode::Enum { name } => {
                if self.deltas.len() < 2 {
                    return;
                }
                let all_changed_bits: BTreeSet<(u32, u8, bool)> = self
                    .deltas
                    .values()
                    .map(|x| x.iter())
                    .flatten()
                    .cloned()
                    .collect();
                let mut bit_sets = self
                    .deltas
                    .values()
                    .map(|d| BTreeSet::from_iter(d.iter().map(|(a, b, v)| (*a, *b, *v))));
                match bit_sets.next() {
                    Some(set0) => {
                        let unchanged_bits = bit_sets.fold(set0, |set1, set2| &set1 & &set2);
                        let changed_bits: BTreeSet<(u32, u8, bool)> = all_changed_bits
                            .difference(&unchanged_bits)
                            .map(|&x| x)
                            .collect();
                        if changed_bits.len() == 0 {
                            return;
                        }
                        for (key, delta) in self.deltas.iter() {
                            if let IPFuzzKey::EnumKey { option } = key {
                                let b = changed_bits
                                    .iter()
                                    .map(|(a, b, v)| ConfigBit {
                                        frame: *a as usize,
                                        bit: *b as usize,
                                        invert: if delta.contains(&(*a, *b, *v)) {
                                            !(*v)
                                        } else {
                                            *v
                                        },
                                    })
                                    .collect();
                                // Add the enum to the tile data
                                let iptype_db = db.ip_bitdb(&self.base.family, &self.iptype);
                                iptype_db.add_enum_option(name, &option, &self.desc, b);
                            }
                        }
                    }
                    None => {}
                }
            }
            IPFuzzMode::Word { name, width } => {
                let mut cbits = Vec::new();
                let mut used_bits = BTreeSet::new();
                for i in 0..*width {
                    let mut deltas = self
                        .deltas
                        .iter()
                        .filter(|(k, _v)| {
                            if let IPFuzzKey::WordKey { bits } = k {
                                bits[i]
                            } else {
                                false
                            }
                        })
                        .map(|(_k, v)| BTreeSet::from_iter(v.iter().map(|(a, b, v)| (*a, *b, *v))));
                    let set0 = deltas.next().unwrap();
                    let is: BTreeSet<(u32, u8, bool)> = deltas
                        .fold(set0, |set1, set2| &set1 & &set2)
                        .difference(&used_bits)
                        .cloned()
                        .collect();
                    cbits.push(
                        is.iter()
                            .map(|(a, b, v)| ConfigBit {
                                frame: *a as usize,
                                bit: *b as usize,
                                invert: !v,
                            })
                            .collect(),
                    );
                    used_bits.append(&mut is.clone());
                }
                let iptype_db = db.ip_bitdb(&self.base.family, &self.iptype);
                iptype_db.add_word(&name, &self.desc, cbits);
            }
        }
        db.flush();
    }
}
