use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::*;

use crate::chip::*;
use crate::database::*;

use itertools::Itertools;
use std::collections::BTreeSet;

pub struct TileLocation {
    tiletypes: Vec<String>,
    neighbours: BTreeSet<Neighbour>,
    pub type_at_loc: Option<usize>,
    pub neigh_type_at_loc: Option<usize>,
}

impl TileLocation {
    pub fn setup(ch: &Chip, x: u32, y: u32, tts: &TileTypes) -> TileLocation {
        let tiles = ch.tiles_by_xy(x, y);
        let tiletypes: Vec<String> = tiles
            .iter()
            .map(|t| t.tiletype.to_string())
            .filter(|tt| tts.get(tt).unwrap().has_routing())
            .collect();
        let neighbours = tiletypes
            .iter()
            .map(|tt| tts.get(tt).unwrap().neighbours.iter())
            .flatten()
            .map(|x| x.clone())
            .collect();
        TileLocation {
            tiletypes: tiletypes,
            neighbours: neighbours,
            type_at_loc: None,
            neigh_type_at_loc: None,
        }
    }
}

pub struct LocationGrid {
    pub width: usize,
    pub height: usize,
    tiles: Vec<TileLocation>,
}

impl LocationGrid {
    pub fn new(ch: &Chip, tts: &TileTypes) -> LocationGrid {
        let width = ch.data.max_col + 1;
        let height = ch.data.max_row + 1;
        let locs = (0..height)
            .cartesian_product(0..width)
            .map(|(y, x)| TileLocation::setup(ch, x as u32, y as u32, tts))
            .collect();
        LocationGrid {
            width: width as usize,
            height: height as usize,
            tiles: locs,
        }
    }
    pub fn get(&self, x: usize, y: usize) -> Option<&TileLocation> {
        if x < self.width && y < self.height {
            Some(&self.tiles[y * self.width + x])
        } else {
            None
        }
    }
    pub fn get_mut(&mut self, x: usize, y: usize) -> Option<&mut TileLocation> {
        if x < self.width && y < self.height {
            Some(&mut self.tiles[y * self.width + x])
        } else {
            None
        }
    }
    // Make the neighbour array symmetric
    pub fn stamp_neighbours(&mut self) {
        for y in 0..self.height {
            for x in 0..self.width {
                let neighbours: Vec<Neighbour> = self
                    .get(x, y)
                    .unwrap()
                    .neighbours
                    .iter()
                    .map(|x| x.clone())
                    .collect();
                for n in neighbours {
                    match n {
                        Neighbour::RelXY { rel_x, rel_y } => {
                            let nx = (x as i32) + rel_x;
                            let ny = (y as i32) + rel_y;
                            if nx >= 0
                                && ny >= 0
                                && (nx as usize) < self.width
                                && (ny as usize) < self.height
                            {
                                let other = self.get_mut(nx as usize, ny as usize).unwrap();
                                other.neighbours.insert(Neighbour::RelXY {
                                    rel_x: -rel_x,
                                    rel_y: -rel_y,
                                });
                            }
                        }
                        _ => {
                            // FIXME: globals
                        }
                    }
                }
            }
        }
    }
}

#[derive(Hash, Eq, PartialEq, Ord, PartialOrd, Clone)]
struct NeighbourType {
    loc: Neighbour,
    loctype: usize,
}

#[derive(Hash, Eq, PartialEq, Clone)]
pub struct NeighbourhoodType {
    neighbours: BTreeSet<NeighbourType>,
}

#[derive(Hash, Eq, PartialEq, Clone)]
pub struct LocTypeKey {
    tiletypes: BTreeSet<String>,
}

pub struct LocTypeData {
    pub wires: IndexedSet<IdString>,
    pub nhtypes: IndexedSet<NeighbourhoodType>,
}

impl LocTypeData {
    pub fn new() -> LocTypeData {
        LocTypeData {
            wires: IndexedSet::new(),
            nhtypes: IndexedSet::new(),
        }
    }
}

pub struct LocationTypes {
    pub types: IndexedMap<LocTypeKey, LocTypeData>,
}

impl LocationTypes {
    pub fn from_locs(lg: &mut LocationGrid) -> LocationTypes {
        let mut lt = LocationTypes {
            types: IndexedMap::new(),
        };
        for y in 0..lg.height {
            for x in 0..lg.width {
                let mut loc = lg.get_mut(x, y).unwrap();

                let loc_key = LocTypeKey {
                    tiletypes: loc.tiletypes.iter().map(|tt| tt.to_string()).collect(),
                };
                let type_idx = lt.types.add(&loc_key, LocTypeData::new());

                loc.type_at_loc = Some(type_idx);
            }
        }
        for y in 0..lg.height {
            for x in 0..lg.width {
                let loc = lg.get(x, y).unwrap();
                let neighbours_with_types = loc
                    .neighbours
                    .iter()
                    .filter_map(|n| match n {
                        Neighbour::RelXY { rel_x, rel_y } => {
                            let nx = (x as i32) + rel_x;
                            let ny = (y as i32) + rel_y;
                            if nx >= 0
                                && ny >= 0
                                && (nx as usize) < lg.width
                                && (ny as usize) < lg.height
                            {
                                Some(NeighbourType {
                                    loc: n.clone(),
                                    loctype: lg.get(nx as usize, ny as usize)?.type_at_loc?,
                                })
                            } else {
                                None
                            }
                        }
                        _ => {
                            // FIXME: globals
                            None
                        }
                    })
                    .collect();
                let loctype = lt.types.value_mut(loc.type_at_loc.unwrap());
                let nt = loctype.nhtypes.add(&NeighbourhoodType {
                    neighbours: neighbours_with_types,
                });
                let mut loc = lg.get_mut(x, y).unwrap();
                loc.neigh_type_at_loc = Some(nt);
            }
        }
        return lt;
    }
    pub fn import_wires(&mut self, _ids: &mut IdStringDB, tts: &TileTypes) {
        for i in 0..self.types.len() {
            // Add wires used within this location, in a FC or pip
            let mut wires = IndexedSet::<IdString>::new();
            {
                let key = self.types.key(i);
                let data = self.types.value(i);
                for wire in key
                    .tiletypes
                    .iter()
                    .map(|tt| tts.get(tt).unwrap().wire_ids.iter())
                    .flatten()
                {
                    wires.add(wire);
                }
                // Add wires used in neighbour tile; but whose nominal location is in this tile
                for nt in data.nhtypes.iter() {
                    for n in nt.neighbours.iter() {
                        let ntt = self.types.key(n.loctype);
                        // Only consider wires where the prefix means they start in this tile
                        let key = match n.loc {
                            Neighbour::RelXY { rel_x, rel_y } => Neighbour::RelXY {
                                rel_x: -rel_x,
                                rel_y: -rel_y,
                            },
                            _ => continue,
                        };
                        for nwire in ntt
                            .tiletypes
                            .iter()
                            .filter_map(|tt| {
                                Some(tts.get(tt).unwrap().neighbour_wire_ids.get(&key)?.iter())
                            })
                            .flatten()
                        {
                            wires.add(nwire);
                        }
                    }
                }
            }
            self.types.value_mut(i).wires = wires;
        }
    }
}
