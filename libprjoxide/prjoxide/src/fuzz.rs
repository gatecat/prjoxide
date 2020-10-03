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
        ignore_tiles: BTreeSet<String>, // changes in these tiles don't cause pips to be rejected
    },
    Word {
        name: String,
        width: usize,
    },
    Enum {
        name: String,
        include_zeros: bool, // if true, explicit 0s instead of base will be created for unset bits for a setting
        disambiguate: bool,  // add explicit 0s to disambiguate settings only
        assume_zero_base: bool,
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
    desc: String,                         // description of the setting being fuzzed
}

impl Fuzzer {
    pub fn init_pip_fuzzer(
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        to_wire: &str,
        fixed_conn_tile: &str,
        ignore_tiles: &BTreeSet<String>,
        full_mux: bool,
        skip_fixed: bool,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Pip {
                to_wire: to_wire.to_string(),
                full_mux: full_mux,
                skip_fixed: skip_fixed,
                fixed_conn_tile: fixed_conn_tile.to_string(),
                ignore_tiles: ignore_tiles.clone(),
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
            desc: "".to_string(),
        }
    }
    pub fn init_word_fuzzer(
        _db: &mut Database,
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        name: &str,
        desc: &str,
        width: usize,
        _zero_bitfile: &str,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Word {
                name: name.to_string(),
                width: width,
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
            desc: desc.to_string(),
        }
    }
    pub fn init_enum_fuzzer(
        base_bit: &Chip,
        fuzz_tiles: &BTreeSet<String>,
        name: &str,
        desc: &str,
        include_zeros: bool,
        assume_zero_base: bool,
    ) -> Fuzzer {
        Fuzzer {
            mode: FuzzMode::Enum {
                name: name.to_string(),
                include_zeros: include_zeros,
                disambiguate: false, // fixme
                assume_zero_base: assume_zero_base,
            },
            tiles: fuzz_tiles.clone(),
            base: base_bit.clone(),
            deltas: BTreeMap::new(),
            desc: desc.to_string(),
        }
    }
    fn add_sample(&mut self, db: &mut Database, key: FuzzKey, bitfile: &str) {
        let parsed_bitstream = BitstreamParser::parse_file(db, bitfile).unwrap();
        let delta: ChipDelta = parsed_bitstream.delta(&self.base);
        if let Some(d) = self.deltas.get_mut(&key) {
            // If key already in delta, take the intersection of the two
            let intersect: ChipDelta = d
                .iter()
                .filter_map(|(tile, td)| match delta.get(tile) {
                    None => None,
                    Some(d2) => {
                        let dv: Vec<(usize, usize, bool)> =
                            td.iter().filter(|x| d2.contains(x)).map(|&x| x).collect();
                        Some((tile.clone(), dv))
                    }
                })
                .collect();
            *d = intersect
        } else {
            self.deltas.insert(key, delta);
        }
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
                ignore_tiles,
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
                        if value
                            .iter()
                            .any(|(k, _v)| !self.tiles.contains(k) && !ignore_tiles.contains(k))
                        {
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
                                            invert: value_bits.iter().any(|x| {
                                                x.contains(&(
                                                    *f,
                                                    *b,
                                                    !self
                                                        .base
                                                        .tile_by_name(tile)
                                                        .unwrap()
                                                        .cram
                                                        .get(*f, *b),
                                                ))
                                            }) == self
                                                .base
                                                .tile_by_name(tile)
                                                .unwrap()
                                                .cram
                                                .get(*f, *b),
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
                                if bits.is_empty() && *skip_fixed {
                                    continue;
                                }
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
                    tile_db.add_word(&name, &self.desc, cbits);
                }
            }
            FuzzMode::Enum {
                name,
                include_zeros,
                disambiguate: _,
                assume_zero_base,
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
                            if changed_bits.len() == 0 {
                                continue;
                            }
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
                                            } else if *assume_zero_base {
                                                changed_bits
                                                    .iter()
                                                    .filter(|(_f, _b, v)| !(*v))
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
                                            .filter(|(f, b, v)| {
                                                !(*assume_zero_base)
                                                    || *v
                                                    || !(*v) && !td.contains(&(*f, *b, *v))
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
                                    tile_db.add_enum_option(name, &option, &self.desc, b);
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

pub fn copy_db(
    db: &mut Database,
    fam: &str,
    from_tt: &str,
    to_tts: &Vec<String>,
    mode: &str,
    pattern: &str,
) {
    let origin_data = db.tile_bitdb(fam, from_tt).db.clone();
    for dest in to_tts {
        let dest_data = db.tile_bitdb(fam, dest);
        if mode.contains('P') {
            // Copy pips
            for (to_wire, pips) in origin_data.pips.iter() {
                for p in pips.iter() {
                    if pattern == "" || to_wire.contains(pattern) || p.from_wire.contains(pattern) {
                        dest_data.add_pip(&p.from_wire, to_wire, p.bits.clone());
                    }
                }
            }
        }
        if mode.contains('E') {
            for (name, opts) in origin_data.enums.iter() {
                if pattern == "" || name.contains(pattern) {
                    for (opt, bits) in opts.options.iter() {
                        dest_data.add_enum_option(name, opt, &opts.desc, bits.clone());
                    }
                }
            }
        }
        if mode.contains('W') {
            for (name, data) in origin_data.words.iter() {
                if pattern == "" || name.contains(pattern) {
                    dest_data.add_word(name, &data.desc, data.bits.clone());
                }
            }
        }
        if mode.contains('C') {
            for (to_wire, conns) in origin_data.conns.iter() {
                for conn in conns.iter() {
                    if pattern == ""
                        || to_wire.contains(pattern)
                        || conn.from_wire.contains(pattern)
                    {
                        dest_data.add_conn(&conn.from_wire, to_wire);
                    }
                }
            }
        }
    }
    db.flush();
}

pub fn add_always_on_bits(
    db: &mut Database,
    ch: &Chip, // chip from 'empty' bitstream
) {
    let all_tiletypes: BTreeSet<String> = ch.tiles.iter().map(|x| x.tiletype.clone()).collect();
    let mut processed_tiletypes: BTreeSet<String> = BTreeSet::new();
    // Start by clearing always_on
    for tt in all_tiletypes.iter() {
        let tdb = db.tile_bitdb(&ch.family, tt);
        tdb.set_always_on(&BTreeSet::new());
    }
    for tile in ch.tiles.iter() {
        let tdb = db.tile_bitdb(&ch.family, &tile.tiletype);
        let mut set_bits = tile.cram.set_bits();
        for pip_bit in tdb
            .db
            .pips
            .values()
            .map(|x| x.iter())
            .flatten()
            .map(|x| x.bits.iter())
            .flatten()
        {
            set_bits.remove(&(pip_bit.frame, pip_bit.bit));
        }
        for word_bit in tdb
            .db
            .words
            .values()
            .map(|x| x.bits.iter())
            .flatten()
            .map(|x| x.iter())
            .flatten()
        {
            set_bits.remove(&(word_bit.frame, word_bit.bit));
        }
        for enum_bit in tdb
            .db
            .enums
            .values()
            .map(|x| x.options.values())
            .flatten()
            .map(|x| x.iter())
            .flatten()
        {
            set_bits.remove(&(enum_bit.frame, enum_bit.bit));
        }
        let always_on: BTreeSet<ConfigBit> = set_bits
            .iter()
            .map(|(f, b)| ConfigBit {
                frame: *f,
                bit: *b,
                invert: false,
            })
            .collect();
        if processed_tiletypes.contains(&tile.tiletype) {
            if always_on != tdb.db.always_on {
                panic!(
                    "mismatched always_on for tile {} of type {} ({:?} vs {:?})",
                    &tile.name, tile.tiletype, &always_on, &tdb.db.always_on
                );
            }
        } else {
            assert!(tdb.db.always_on.is_empty());
            tdb.set_always_on(&always_on);
        }

        processed_tiletypes.insert(tile.tiletype.clone());
    }
    db.flush();
}
