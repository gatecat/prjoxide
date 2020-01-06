use crate::bba::bbastruct::*;
use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::*;

use crate::chip::*;

use itertools::Itertools;
use std::collections::{BTreeSet, HashMap};
use std::convert::TryInto;

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

pub struct NeighbourhoodData {
    pub neigh_arcs: IndexedSet<NeighbourArc>,
}

impl NeighbourhoodData {
    pub fn new() -> NeighbourhoodData {
        NeighbourhoodData {
            neigh_arcs: IndexedSet::new(),
        }
    }
}

#[derive(Hash, Eq, PartialEq, Clone)]
pub struct LocTypeKey {
    tiletypes: BTreeSet<String>,
}

// A connection
#[derive(Hash, Eq, PartialEq, Ord, PartialOrd, Clone)]
pub struct NeighbourArc {
    pub this_loc_wire: IdString,
    pub other_loc_wire: IdString,
    pub other_loc: Neighbour,
    pub is_driving: bool,
    pub to_primary: bool,
}

pub struct LocTypeData {
    pub wires: IndexedSet<IdString>,
    pub primary_wires: BTreeSet<IdString>,
    pub nhtypes: IndexedMap<NeighbourhoodType, NeighbourhoodData>,
}

impl LocTypeData {
    pub fn new() -> LocTypeData {
        LocTypeData {
            wires: IndexedSet::new(),
            primary_wires: BTreeSet::new(),
            nhtypes: IndexedMap::new(),
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
                let nt = loctype.nhtypes.add(
                    &NeighbourhoodType {
                        neighbours: neighbours_with_types,
                    },
                    NeighbourhoodData::new(),
                );
                let mut loc = lg.get_mut(x, y).unwrap();
                loc.neigh_type_at_loc = Some(nt);
            }
        }
        return lt;
    }
    pub fn import_wires(&mut self, _ids: &mut IdStringDB, tts: &TileTypes) {
        // Import just the wires
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
                for (nt, _) in data.nhtypes.iter() {
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
                            wires.add(&nwire.neigh_name);
                        }
                    }
                }
            }
            self.types.value_mut(i).wires = wires;
        }
        // Import the n-n arcs
        let mut _arcs_count = 0;
        for i in 0..self.types.len() {
            for j in 0..self.types.value(i).nhtypes.len() {
                let mut arcs: IndexedSet<NeighbourArc> = IndexedSet::new();
                let mut primary_wires: BTreeSet<IdString> =
                    self.types.value(i).wires.iter().cloned().collect();
                {
                    let key = self.types.key(i);
                    let data = self.types.value(i);
                    let loc_driven_wires: BTreeSet<IdString> = key
                        .tiletypes
                        .iter()
                        .map(|tt| tts.get(tt).unwrap().driven_wire_ids.iter())
                        .flatten()
                        .cloned()
                        .collect();
                    // Arcs to where the base location of the wire is _not_ this location
                    for (neigh, nwires) in key
                        .tiletypes
                        .iter()
                        .map(|tt| tts.get(tt).unwrap().neighbour_wire_ids.iter())
                        .flatten()
                    {
                        // FIXME: multiply driven wires?
                        for nwire in nwires.iter() {
                            let is_driven_by_us = loc_driven_wires.contains(&nwire.our_name);
                            primary_wires.remove(&nwire.our_name);
                            arcs.add(&NeighbourArc {
                                this_loc_wire: nwire.our_name,
                                other_loc: neigh.clone(),
                                other_loc_wire: nwire.neigh_name,
                                is_driving: is_driven_by_us,
                                to_primary: true,
                            });
                        }
                    }
                    // Arcs from neighbours where the base location of the wire _is_ this location
                    let nt = data.nhtypes.key(j);
                    for n in nt.neighbours.iter() {
                        let ntt = self.types.key(n.loctype);
                        // Only consider wires where the prefix means they start in this tile
                        if let Neighbour::RelXY { rel_x, rel_y } = n.loc {
                            let key = Neighbour::RelXY {
                                rel_x: -rel_x,
                                rel_y: -rel_y,
                            };
                            for nwire in ntt
                                .tiletypes
                                .iter()
                                .filter_map(|tt| {
                                    Some(tts.get(tt).unwrap().neighbour_wire_ids.get(&key)?.iter())
                                })
                                .flatten()
                            {
                                let is_driven_by_them = ntt.tiletypes.iter().any(|tt| {
                                    tts.get(tt)
                                        .unwrap()
                                        .driven_wire_ids
                                        .contains(&nwire.our_name)
                                });
                                arcs.add(&NeighbourArc {
                                    this_loc_wire: nwire.neigh_name,
                                    other_loc: n.loc.clone(),
                                    other_loc_wire: nwire.our_name,
                                    is_driving: !is_driven_by_them,
                                    to_primary: false,
                                });
                            }
                        }
                    }
                }
                _arcs_count += arcs.len();
                self.types.value_mut(i).nhtypes.value_mut(j).neigh_arcs = arcs;
            }
        }
    }

    pub fn write_locs_bba(
        &self,
        out: &mut BBAStructs,
        ids: &mut IdStringDB,
        tts: &TileTypes,
    ) -> std::io::Result<()> {
        for (i, (key, data)) in self.types.iter().enumerate() {
            // Wire -> bel, pin
            let mut wire_belpins = HashMap::<usize, Vec<(usize, IdString)>>::new();
            // Wire -> pip ids
            let mut wire_uphill = HashMap::<usize, Vec<usize>>::new();
            let mut wire_downhill = HashMap::<usize, Vec<usize>>::new();
            // Lists of bel pins
            for (j, bel) in key
                .tiletypes
                .iter()
                .map(|tt| tts.get(tt).unwrap().bels.iter())
                .flatten()
                .enumerate()
            {
                out.list_begin(&format!("tt{}w{}_belpins", i, j))?;
                // Bel pins, sorted by ID for binary searchability
                let mut ports = bel.pins.clone();
                ports.sort_by(|p1, p2| {
                    ids.id(&p1.name)
                        .val()
                        .partial_cmp(&ids.id(&p2.name).val())
                        .unwrap()
                });
                for port in ports.iter() {
                    let wire_idx = data
                        .wires
                        .get_index(&ids.id(&port.wire.rel_name()))
                        .unwrap();
                    wire_belpins
                        .entry(wire_idx)
                        .or_insert(Vec::new())
                        .push((j, ids.id(&port.name)));
                    out.bel_wire(ids.id(&port.name), port.dir.clone(), wire_idx)?;
                }
            }
            // Lists of bels
            out.list_begin(&format!("tt{}_bels", i))?;
            for (j, bel) in key
                .tiletypes
                .iter()
                .map(|tt| tts.get(tt).unwrap().bels.iter())
                .flatten()
                .enumerate()
            {
                out.bel_info(
                    ids.id(&bel.name),
                    ids.id(&bel.beltype),
                    0,
                    0,
                    &format!("tt{}w{}_belpins", i, j),
                    bel.pins.len(),
                )?;
            }
            // Lists of pips
            out.list_begin(&format!("tt{}_pips", i))?;
            let mut pip_index = 0;
            for tt in key.tiletypes.iter() {
                let tt_id = ids.id(tt);
                // Real pips
                for (to_wire, pips) in tts.get(tt).unwrap().data.pips.iter() {
                    let to_wire_idx = data.wires.get_index(&ids.id(to_wire)).unwrap();
                    for pip in pips.iter() {
                        let from_wire_idx = data.wires.get_index(&ids.id(&pip.from_wire)).unwrap();
                        wire_downhill
                            .entry(from_wire_idx)
                            .or_insert(Vec::new())
                            .push(pip_index);
                        wire_uphill
                            .entry(to_wire_idx)
                            .or_insert(Vec::new())
                            .push(pip_index);
                        out.tile_pip(from_wire_idx, to_wire_idx, tt_id)?;
                        pip_index += 1;
                    }
                }
                // Fixed connections; also represented as pips
                for (to_wire, conns) in tts.get(tt).unwrap().data.conns.iter() {
                    let to_wire_idx = data.wires.get_index(&ids.id(to_wire)).unwrap();
                    for pip in conns.iter() {
                        let from_wire_idx = data.wires.get_index(&ids.id(&pip.from_wire)).unwrap();
                        wire_downhill
                            .entry(from_wire_idx)
                            .or_insert(Vec::new())
                            .push(pip_index);
                        wire_uphill
                            .entry(to_wire_idx)
                            .or_insert(Vec::new())
                            .push(pip_index);
                        out.tile_pip(from_wire_idx, to_wire_idx, tt_id)?;
                        pip_index += 1;
                    }
                }
            }
            // Lists of neighbour wires
            for (j, (ntype, ndata)) in data.nhtypes.iter().enumerate() {
                let mut arcs_by_wire_idx = HashMap::<usize, Vec<&NeighbourArc>>::new();
                for arc in ndata.neigh_arcs.iter() {
                    arcs_by_wire_idx
                        .entry(data.wires.get_index(&arc.this_loc_wire).unwrap())
                        .or_insert(Vec::new())
                        .push(&arc);
                }
                for k in 0..data.wires.len() {
                    out.list_begin(&format!("tt{}_nh{}_w{}", i, j, k))?;
                    for arc in arcs_by_wire_idx.get(&k).iter().map(|x| x.iter()).flatten() {
                        match arc.other_loc {
                            Neighbour::RelXY { rel_x, rel_y } => {
                                let other_loc_type = match ntype
                                    .neighbours
                                    .iter()
                                    .find(|n| n.loc == arc.other_loc)
                                {
                                    None => continue,
                                    Some(x) => x,
                                }
                                .loctype;
                                let other_loc_idx = self
                                    .types
                                    .value(other_loc_type)
                                    .wires
                                    .get_index(&arc.other_loc_wire)
                                    .unwrap();

                                let mut arc_flags = 0;

                                if arc.is_driving {
                                    arc_flags |= PHYSICAL_DOWNHILL;
                                }
                                if arc.to_primary {
                                    arc_flags |= LOGICAL_TO_PRIMARY;
                                }
                                out.rel_wire(
                                    0,
                                    arc_flags,
                                    rel_x.try_into().unwrap(),
                                    rel_y.try_into().unwrap(),
                                    other_loc_idx,
                                )?;
                            }
                            _ => continue,
                        }
                    }
                }
            }
        }
        Ok(())
    }
}
