use crate::bitstream::*;
use crate::chip::*;
use crate::database::*;
use std::collections::{BTreeMap, BTreeSet};

pub enum FuzzMode {
    Pip {
        to_wire: String,
        full_mux: bool, // if true, explicit 0s instead of empty will be created for unset bits for a setting
        skip_fixed: bool, // if true, skip pips that have no bits associated with them (rather than created fixed conns)
        fixed_conn_tile: String,
    },
    Word {
        name: String,
        width: usize,
    },
    Enum {
        name: String,
        include_zeros: bool, // if true, explicit 0s instead of empty will be created for unset bits for a setting
        disambiguate: bool,  // add explicit 0s to disambiguate settings only
    },
}

#[derive(PartialEq, Eq, PartialOrd, Ord, Clone)]
enum FuzzKey {
    PipKey { from_wire: String },
    WordKey { bit: Option<usize> },
    EnumKey { option: String },
}

pub struct Fuzzer<'a> {
    mode: FuzzMode,
    tiles: BTreeSet<String>,
    empty: &'a Chip,                      // bitstream with nothing set
    deltas: BTreeMap<FuzzKey, ChipDelta>, // used for arcs and words
    tilebits: BTreeMap<FuzzKey, Vec<BTreeMap<String, BitMatrix>>>, // used for enums
}

impl Fuzzer<'_> {
    pub fn init_pip_fuzzer<'a>(
        empty_bit: &'a Chip,
        fuzz_tiles: &BTreeSet<String>,
        to_wire: &str,
        fixed_conn_tile: &str,
        full_mux: bool,
        skip_fixed: bool,
    ) -> Fuzzer<'a> {
        Fuzzer {
            mode: FuzzMode::Pip {
                to_wire: to_wire.to_string(),
                full_mux: full_mux,
                skip_fixed: skip_fixed,
                fixed_conn_tile: fixed_conn_tile.to_string(),
            },
            tiles: fuzz_tiles.clone(),
            empty: empty_bit,
            deltas: BTreeMap::new(),
            tilebits: BTreeMap::new(),
        }
    }
    pub fn add_pip_sample(&mut self, db: &mut Database, from_wire: &str, bitfile: &str) {
        let parsed_bitstream = BitstreamParser::parse_file(db, bitfile).unwrap();
        let delta = parsed_bitstream.delta(self.empty);
        let key = FuzzKey::PipKey {
            from_wire: from_wire.to_string(),
        };
        self.deltas.insert(key, delta);
    }
    pub fn solve(&mut self, db: &mut Database) {
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
                        if value.len() == 0 && (!(*full_mux) || self.deltas.len() == 1) {
                            // Value has no changes; it is a fixed connection
                            if *skip_fixed {
                                continue;
                            }
                            let db_tile = self.empty.tile_by_name(fixed_conn_tile).unwrap();
                            let tile_db = db.tile_bitdb(&self.empty.family, &db_tile.tiletype);
                            tile_db.add_conn(&from_wire, to_wire);
                        } else {
                            for tile in self.tiles.iter() {
                                if !(*full_mux) && !value.contains_key(tile) {
                                    continue;
                                }
                                // Get the set of bits for this config
                                let bits = if *full_mux {
                                } else {
                                };
                            }
                        }
                    }
                }
            }
            FuzzMode::Word { name, width } => {}
            FuzzMode::Enum {
                name,
                include_zeros,
                disambiguate,
            } => {}
        }
    }
}
