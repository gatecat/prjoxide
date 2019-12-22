use crate::bitstream::*;
use crate::chip::*;
use crate::database::*;
use crate::wires;
use std::collections::{BTreeMap, BTreeSet};
use std::iter::FromIterator;

pub enum FuzzMode {
    Pip {
        to_wire: String,
        full_mux: bool, // if true, explicit 0s instead of base will be created for unset bits for a setting
        skip_fixed: bool, // if true, skip pips that have no bits associated with them (rather than created fixed conns)
        fixed_conn_tile: String,
    },
    Word {
        name: String,
        width: usize,
    },
    Enum {
        name: String,
        include_zeros: bool, // if true, explicit 0s instead of base will be created for unset bits for a setting
        disambiguate: bool,  // add explicit 0s to disambiguate settings only
    },
}

#[derive(PartialEq, Eq, PartialOrd, Ord, Clone)]
enum FuzzKey {
    PipKey { from_wire: String },
    WordKey { bit: usize },
    EnumKey { option: String },
}

pub struct Fuzzer {
    mode: FuzzMode,
    tiles: BTreeSet<String>,
    base: Chip,                           // bitstream with nothing set
    deltas: BTreeMap<FuzzKey, ChipDelta>, // used for arcs, words and enums
}

impl Fuzzer {
    pub fn init_pip_fuzzer(
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        to_wire: &str,
        fixed_conn_tile: &str,
        full_mux: bool,
        skip_fixed: bool,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Pip {
                to_wire: to_wire.to_string(),
                full_mux: full_mux,
                skip_fixed: skip_fixed,
                fixed_conn_tile: fixed_conn_tile.to_string(),
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
        }
    }
    pub fn init_word_fuzzer(
        db: &mut Database,
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        name: &str,
        width: usize,
        zero_bitfile: &str,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Word {
                name: name.to_string(),
                width: width,
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
        }
    }
    pub fn init_enum_fuzzer(
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        name: &str,
        include_zeros: bool,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Enum {
                name: name.to_string(),
                include_zeros: include_zeros,
                disambiguate: false, // fixme
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
        }
    }
    fn add_sample(&mut self, db: &mut Database, key: FuzzKey, bitfile: &str) {
        let parsed_bitstream = BitstreamParser::parse_file(db, bitfile).unwrap();
        let delta = parsed_bitstream.delta(&self.base);
        self.deltas.insert(key, delta);
    }
    pub fn add_pip_sample(&mut self, db: &mut Database, from_wire: &str, bitfile: &str) {
        self.add_sample(
            db,
            FuzzKey::PipKey {
                from_wire: from_wire.to_string(),
            },
            bitfile,
        );
    }
    pub fn add_word_sample(&mut self, db: &mut Database, index: usize, bitfile: &str) {
        self.add_sample(db, FuzzKey::WordKey { bit: index }, bitfile);
    }
    pub fn add_enum_sample(&mut self, db: &mut Database, option: &str, bitfile: &str) {
        self.add_sample(
            db,
            FuzzKey::EnumKey {
                option: option.to_string(),
            },
            bitfile,
        );
    }
    pub fn solve(&mut self, db: &mut Database) {
        // Get a set of tiles that have been changed
        let changed_tiles: BTreeSet<String> = self
            .deltas
            .iter()
            .flat_map(|(_k, v)| v.keys())
            .filter(|t| self.tiles.contains(*t))
            .map(String::to_string)
            .collect();
        match &self.mode {
            FuzzMode::Pip {
                to_wire,
                full_mux,
                skip_fixed,
                fixed_conn_tile,
            } => {
                // In full mux mode; we need the coverage sets of the changes
                let mut coverage: BTreeMap<String, BTreeSet<(usize, usize)>> = BTreeMap::new();
                if *full_mux {
                    for tile in self.tiles.iter() {
                        coverage.insert(
                            tile.to_string(),
                            self.deltas
                                .iter()
                                .filter_map(|(_k, v)| v.get(tile))
                                .flatten()
                                .map(|(f, b, _v)| (*f, *b))
                                .collect(),
                        );
                    }
                }

                for (key, value) in self.deltas.iter() {
                    if let FuzzKey::PipKey { from_wire } = key {
                        if value.iter().any(|(k, _v)| !self.tiles.contains(k)) {
                            // If this pip affects tiles outside of the fuzz region, skip it
                            continue;
                        }
                        if changed_tiles.len() == 0 {
                            // No changes; it is a fixed connection
                            if *skip_fixed {
                                continue;
                            }
                            let db_tile = self.base.tile_by_name(fixed_conn_tile).unwrap();
                            let tile_db = db.tile_bitdb(&self.base.family, &db_tile.tiletype);
                            tile_db.add_conn(
                                &wires::normalize_wire(&self.base, db_tile, from_wire),
                                &wires::normalize_wire(&self.base, db_tile, to_wire),
                            );
                        } else {
                            for tile in changed_tiles.iter() {
                                // Get the set of bits for this config
                                let bits: BTreeSet<ConfigBit> = if *full_mux {
                                    // In full mux mode, we add a value for all bits even if they didn't change
                                    let value_bits = value.get(tile);
                                    coverage
                                        .get(tile)
                                        .iter()
                                        .map(|&x| x)
                                        .flatten()
                                        .map(|(f, b)| ConfigBit {
                                            frame: *f,
                                            bit: *b,
                                            invert: value_bits
                                                .iter()
                                                .any(|x| x.contains(&(*f, *b, true))),
                                        })
                                        .collect()
                                } else {
                                    // Get the changed bits in this tile as ConfigBits; or the base set if the tile didn't change
                                    value
                                        .get(tile)
                                        .iter()
                                        .map(|&x| x)
                                        .flatten()
                                        .map(|(f, b, v)| ConfigBit {
                                            frame: *f,
                                            bit: *b,
                                            invert: !(*v),
                                        })
                                        .collect()
                                };
                                // Add the pip to the tile data
                                let tile_data = self.base.tile_by_name(tile).unwrap();
                                let tile_db = db.tile_bitdb(&self.base.family, &tile_data.tiletype);
                                tile_db.add_pip(
                                    &wires::normalize_wire(&self.base, tile_data, from_wire),
                                    &wires::normalize_wire(&self.base, tile_data, to_wire),
                                    bits,
                                );
                            }
                        }
                    }
                }
            }
            FuzzMode::Word { name, width } => {
                for tile in changed_tiles.iter() {
                    let mut cbits = Vec::new();
                    for i in 0..*width {
                        let key = FuzzKey::WordKey { bit: i };
                        let b = match self.deltas.get(&key) {
                            None => BTreeSet::new(),
                            Some(delta) => match delta.get(tile) {
                                None => BTreeSet::new(),
                                Some(td) => td
                                    .iter()
                                    .map(|(f, b, v)| ConfigBit {
                                        frame: *f,
                                        bit: *b,
                                        invert: !(*v),
                                    })
                                    .collect(),
                            },
                        };
                        cbits.push(b);
                    }
                    // Add the word to the tile data
                    let tile_data = self.base.tile_by_name(tile).unwrap();
                    let tile_db = db.tile_bitdb(&self.base.family, &tile_data.tiletype);
                    tile_db.add_word(&name, cbits);
                }
            }
            FuzzMode::Enum {
                name,
                include_zeros,
                disambiguate: _,
            } => {
                if self.deltas.len() < 2 {
                    return;
                }
                for tile in changed_tiles {
                    let mut bit_sets = self.deltas.values().map(|v| match v.get(&tile) {
                        Some(td) => BTreeSet::from_iter(td.iter().map(|(f, b, v)| (*f, *b, *v))),
                        None => BTreeSet::new(),
                    });
                    let all_changed_bits: BTreeSet<(usize, usize, bool)> = self
                        .deltas
                        .values()
                        .filter_map(|v| v.get(&tile))
                        .flatten()
                        .map(|&x| x)
                        .collect();
                    match bit_sets.next() {
                        None => continue, // no changes in this tile
                        Some(set0) => {
                            let unchanged_bits = bit_sets.fold(set0, |set1, set2| &set1 & &set2);
                            let changed_bits: BTreeSet<(usize, usize, bool)> = all_changed_bits
                                .difference(&unchanged_bits)
                                .map(|&x| x)
                                .collect();
                            for (key, delta) in self.deltas.iter() {
                                if let FuzzKey::EnumKey { option } = key {
                                    let b = match delta.get(&tile) {
                                        None => {
                                            if *include_zeros {
                                                // All bits as default
                                                changed_bits
                                                    .iter()
                                                    .map(|(f, b, v)| ConfigBit {
                                                        frame: *f,
                                                        bit: *b,
                                                        invert: *v,
                                                    })
                                                    .collect()
                                            } else {
                                                BTreeSet::new()
                                            }
                                        }
                                        Some(td) => changed_bits
                                            .iter()
                                            .filter(|(f, b, v)| {
                                                *include_zeros
                                                    || !(*v)
                                                    || td.contains(&(*f, *b, *v))
                                            })
                                            .map(|(f, b, v)| ConfigBit {
                                                frame: *f,
                                                bit: *b,
                                                invert: if td.contains(&(*f, *b, *v)) {
                                                    !(*v)
                                                } else {
                                                    *v
                                                },
                                            })
                                            .collect(),
                                    };
                                    // Add the enum to the tile data
                                    let tile_data = self.base.tile_by_name(&tile).unwrap();
                                    let tile_db =
                                        db.tile_bitdb(&self.base.family, &tile_data.tiletype);
                                    tile_db.add_enum_option(name, &option, b);
                                }
                            }
                        }
                    }
                }
            }
        }
        db.flush();
    }
}
