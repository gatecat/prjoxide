use crate::bba::bbastruct::*;
use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::*;

use crate::chip::*;
use crate::database::*;

use itertools::Itertools;
use std::collections::{BTreeSet, HashMap};
use std::convert::TryInto;

pub struct TileLocation {
    tiletypes: Vec<String>,
    // Neighbour; inverse neighbour for wire matching if applicable
    neighbours: BTreeSet<(Neighbour, Option<Neighbour>)>,
    pub type_at_loc: Option<usize>,
    pub neigh_type_at_loc: Option<usize>,
}

impl TileLocation {
    pub fn setup(
        ch: &Chip,
        x: u32,
        y: u32,
        glb: &DeviceGlobalsData,
        tts: &TileTypes,
    ) -> TileLocation {
        let tiles = ch.tiles_by_xy(x, y);
        let mut tiletypes: Vec<String> = tiles
            .iter()
            .map(|t| t.tiletype.to_string())
            .filter(|tt| tts.get(tt).unwrap().has_routing())
            .collect();
        // (0, 0) is a special case as we keep all the global signals here,
        // but don't want to pollute other null tiles
        if x == 0 && y == 0 {
            tiletypes.push("GLOBAL_ORIGIN".to_string());
        }
        // Other special global locations
        if let Some(side) = glb.is_branch_loc(x as usize) {
            tiletypes.push(format!("GLOBAL_BRANCH_{}", side));
        }
        if glb.is_spine_loc(x as usize, y as usize) {
            tiletypes.push("GLOBAL_SPINE_ORIGIN".to_string());
        }
        if glb.is_hrow_loc(x as usize, y as usize) {
            tiletypes.push("GLOBAL_HROW_ORIGIN".to_string());
        }
        let neighbours = tiletypes
            .iter()
            .map(|tt| tts.get(tt).unwrap().neighbours.iter())
            .flatten()
            .map(|x| (x.clone(), None))
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
    glb: DeviceGlobalsData,
}

impl LocationGrid {
    pub fn new(ch: &Chip, db: &mut Database, tts: &TileTypes) -> LocationGrid {
        let width = ch.data.max_col + 1;
        let height = ch.data.max_row + 1;
        let globals = db.device_globals(&ch.family, &ch.device);
        let locs = (0..height)
            .cartesian_product(0..width)
            .map(|(y, x)| TileLocation::setup(ch, x as u32, y as u32, globals, tts))
            .collect();
        LocationGrid {
            width: width as usize,
            height: height as usize,
            tiles: locs,
            glb: globals.clone(),
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
    // Convert a neighbour to a coordinate
    pub fn neighbour_tile(&self, x: usize, y: usize, n: &Neighbour) -> Option<(usize, usize)> {
        match n {
            Neighbour::RelXY { rel_x, rel_y } => {
                let nx = (x as i32) + rel_x;
                let ny = (y as i32) + rel_y;
                if nx >= 0 && ny >= 0 && (nx as usize) < self.width && (ny as usize) < self.height {
                    Some((nx as usize, ny as usize))
                } else {
                    None
                }
            }
            Neighbour::Global => {
                if x != 0 || y != 0 {
                    Some((0, 0))
                } else {
                    None
                }
            }
            Neighbour::Branch => {
                let branch_col = self.glb.branch_sink_to_origin(x).unwrap();
                Some((branch_col, y))
            }
            Neighbour::BranchDriver { side } => {
                let offset: i32 = match side {
                    BranchSide::Right => 2,
                    BranchSide::Left => -2,
                };
                let branch_col = self
                    .glb
                    .branch_sink_to_origin((x as i32 + offset) as usize)
                    .unwrap();
                Some((branch_col, y))
            }
            Neighbour::Spine => return Some(self.glb.spine_sink_to_origin(x, y).unwrap()),
            Neighbour::HRow => return Some(self.glb.hrow_sink_to_origin(x, y).unwrap()),
            _ => None,
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
                    .map(|x| x.0.clone())
                    .collect();
                for n in neighbours {
                    let nt = self.neighbour_tile(x, y, &n);
                    if let Some((nx, ny)) = nt {
                        let other = self.get_mut(nx as usize, ny as usize).unwrap();
                        other.neighbours.insert((
                            Neighbour::RelXY {
                                rel_x: (x as i32) - (nx as i32),
                                rel_y: (y as i32) - (ny as i32),
                            },
                            Some(n),
                        ));
                    }
                }
            }
        }
    }
    // Write grid info to the bba
    pub fn write_grid_bba(
        &self,
        out: &mut BBAStructs,
        device_idx: u32,
        ids: &mut IdStringDB,
        ch: &Chip,
    ) -> std::io::Result<()> {
        // Lists of physical tiles at a location
        let mut num_phys_tiles = vec![0; self.height * self.width];
        let mut loc_flags = vec![0; self.height * self.width];
        for y in 0..self.height {
            for x in 0..self.width {
                let phys_tiles = ch.tiles_by_xy(x as u32, y as u32);
                num_phys_tiles[y * self.width + x] = phys_tiles.len();
                out.list_begin(&format!("d{}_y{}x{}_ptiles", device_idx, y, x))?;
                let mut flags = 0;
                for tile in phys_tiles.iter() {
                    let colon_pos = tile.name.find(':').unwrap();
                    let tiletype_str = &tile.name[colon_pos + 1..];
                    let tiletype = ids.id(tiletype_str);
                    let mut prefix_end = tile.name[0..colon_pos].rfind('_').unwrap_or(0);
                    if prefix_end != 0 {
                        prefix_end += 1;
                    }
                    let prefix = ids.id(&tile.name[0..prefix_end]);
                    if tiletype_str == "PLC" {
                        flags |= LOC_LOGIC;
                    } else if tiletype_str.starts_with("SYSIO_B5")
                        || tiletype_str.starts_with("SYSIO_B4")
                        || tiletype_str.starts_with("SYSIO_B3")
                    {
                        flags |= LOC_IO18;
                    } else if tiletype_str.starts_with("SYSIO_B0")
                        || tiletype_str.starts_with("SYSIO_B1")
                        || tiletype_str.starts_with("SYSIO_B2")
                        || tiletype_str.starts_with("SYSIO_B6")
                        || tiletype_str.starts_with("SYSIO_B7")
                    {
                        flags |= LOC_IO33;
                    } else if tiletype_str.starts_with("EBR_") {
                        flags |= LOC_BRAM;
                    } else if tiletype_str.starts_with("DSP_") {
                        flags |= LOC_DSP;
                    } else if tiletype_str.starts_with("CIB") {
                        flags |= LOC_CIB;
                    } else if tiletype_str.starts_with("TAP_") {
                        flags |= LOC_TAP;
                    } else if tiletype_str.starts_with("SPINE_") {
                        flags |= LOC_SPINE;
                    } else if tiletype_str.starts_with("TRUNK") {
                        flags |= LOC_TRUNK;
                    }
                    out.physical_tile(prefix, tiletype)?;
                }
                loc_flags[y * self.width + x] = flags;
            }
        }
        // Actual grid data
        out.list_begin(&format!("d{}_grid", device_idx))?;
        for y in 0..self.height {
            for x in 0..self.width {
                let data = self.get(x, y).unwrap();
                out.grid_loc(
                    data.type_at_loc.unwrap(),
                    loc_flags[y * self.width + x],
                    data.neigh_type_at_loc.unwrap(),
                    num_phys_tiles[y * self.width + x],
                    &format!("d{}_y{}x{}_ptiles", device_idx, y, x),
                )?;
            }
        }
        Ok(())
    }
    // Write out the bba for a chip type
    pub fn write_chip_bba(
        &self,
        out: &mut BBAStructs,
        device_idx: u32,
        ch: &Chip,
    ) -> std::io::Result<()> {
        out.device(
            &ch.device,
            self.width,
            self.height,
            self.height * self.width,
            &format!("d{}_grid", device_idx),
        )?;
        Ok(())
    }
}

#[derive(Hash, Eq, PartialEq, Ord, PartialOrd, Clone)]
struct NeighbourType {
    loc: Neighbour,
    loctype: usize,
    inv_wire_loc: Option<Neighbour>,
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
                    .filter_map(|(n, invn)| {
                        let (nx, ny) = lg.neighbour_tile(x, y, n)?;
                        Some(NeighbourType {
                            loc: n.clone(),
                            loctype: lg.get(nx as usize, ny as usize)?.type_at_loc?,
                            inv_wire_loc: invn.clone(),
                        })
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
                        if let Some(iwl) = &n.inv_wire_loc {
                            let ntt = self.types.key(n.loctype);
                            // Only consider wires where the prefix means they start in this tile
                            for nwire in ntt
                                .tiletypes
                                .iter()
                                .filter_map(|tt| {
                                    Some(tts.get(tt).unwrap().neighbour_wire_ids.get(iwl)?.iter())
                                })
                                .flatten()
                            {
                                wires.add(&nwire.neigh_name);
                            }
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
                        if let Neighbour::RelXY { rel_x: _, rel_y: _ } = n.loc {
                            if let Some(iwl) = &n.inv_wire_loc {
                                for nwire in ntt
                                    .tiletypes
                                    .iter()
                                    .filter_map(|tt| {
                                        Some(
                                            tts.get(tt)
                                                .unwrap()
                                                .neighbour_wire_ids
                                                .get(iwl)?
                                                .iter(),
                                        )
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
        let mut tt_pip_count = vec![0; self.types.len()];
        let mut tt_bel_count = vec![0; self.types.len()];

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
                out.list_begin(&format!("tt{}b{}_bw", i, j))?;
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
                    bel.z,
                    &format!("tt{}b{}_bw", i, j),
                    bel.pins.len(),
                )?;
                *tt_bel_count.get_mut(i).unwrap() += 1;
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
                        out.tile_pip(from_wire_idx, to_wire_idx, 0, tt_id)?;
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
                        out.tile_pip(from_wire_idx, to_wire_idx, PIP_FIXED_CONN, tt_id)?;
                        pip_index += 1;
                    }
                }
            }
            *tt_pip_count.get_mut(i).unwrap() = pip_index;
            // Wire pip and bel lists
            for (j, _) in data.wires.iter().enumerate() {
                let empty_pip_vec = vec![];
                let uphill = wire_uphill.get(&j).unwrap_or(&empty_pip_vec);
                let downhill = wire_downhill.get(&j).unwrap_or(&empty_pip_vec);
                let empty_pin_vec = vec![];
                let belpins = wire_belpins.get(&j).unwrap_or(&empty_pin_vec);
                out.pips_list(&format!("t{}_w{}_uh", i, j), &uphill)?;
                out.pips_list(&format!("t{}_w{}_dh", i, j), &downhill)?;
                out.list_begin(&format!("t{}_w{}_bp", i, j))?;
                for (bel, pin) in belpins.iter() {
                    out.bel_pin(*bel, *pin)?;
                }
            }
            // Lists of wires
            out.list_begin(&format!("tt{}_wires", i))?;
            for (j, wirename) in data.wires.iter().enumerate() {
                let empty_pip_vec = vec![];
                let uphill = wire_uphill.get(&j).unwrap_or(&empty_pip_vec);
                let downhill = wire_downhill.get(&j).unwrap_or(&empty_pip_vec);
                let empty_pin_vec = vec![];
                let belpins = wire_belpins.get(&j).unwrap_or(&empty_pin_vec);
                let mut flags = 0;
                if data.primary_wires.contains(wirename) {
                    flags |= WIRE_PRIMARY;
                }
                out.tile_wire(
                    wirename.clone(),
                    flags,
                    &format!("t{}_w{}_uh", i, j),
                    &format!("t{}_w{}_dh", i, j),
                    &format!("t{}_w{}_bp", i, j),
                    uphill.len(),
                    downhill.len(),
                    belpins.len(),
                )?;
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
                let mut neigh_wire_count = vec![0; data.wires.len()];
                for k in 0..data.wires.len() {
                    out.list_begin(&format!("tt{}_nh{}_w{}", i, j, k))?;
                    for arc in arcs_by_wire_idx.get(&k).iter().map(|x| x.iter()).flatten() {
                        let mut arc_rel_x = 0;
                        let mut arc_rel_y = 0;
                        let rel_type;
                        let other_loc_type =
                            match ntype.neighbours.iter().find(|n| n.loc == arc.other_loc) {
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
                        match &arc.other_loc {
                            Neighbour::RelXY { rel_x, rel_y } => {
                                arc_rel_x = *rel_x;
                                arc_rel_y = *rel_y;
                                rel_type = REL_LOC_XY;
                            }
                            Neighbour::Global => {
                                rel_type = REL_LOC_GLOBAL;
                            }
                            Neighbour::Branch => {
                                rel_type = REL_LOC_BRANCH;
                            }
                            Neighbour::BranchDriver { side } => match side {
                                BranchSide::Left => {
                                    rel_type = REL_LOC_BRANCH_L;
                                }
                                BranchSide::Right => {
                                    rel_type = REL_LOC_BRANCH_R;
                                }
                            },
                            Neighbour::Spine => {
                                rel_type = REL_LOC_SPINE;
                            }
                            Neighbour::HRow => {
                                rel_type = REL_LOC_HROW;
                            }
                            _ => continue,
                        }
                        let mut arc_flags = 0;

                        if arc.is_driving {
                            arc_flags |= PHYSICAL_DOWNHILL;
                        }
                        if arc.to_primary {
                            arc_flags |= LOGICAL_TO_PRIMARY;
                        }
                        out.rel_wire(
                            rel_type,
                            arc_flags,
                            arc_rel_x.try_into().unwrap(),
                            arc_rel_y.try_into().unwrap(),
                            other_loc_idx,
                        )?;
                        *neigh_wire_count.get_mut(k).unwrap() += 1;
                    }
                }
                out.list_begin(&format!("tt{}_nh{}_wires", i, j))?;
                for (k, wc) in neigh_wire_count.iter().enumerate() {
                    out.wire_neighbours(&format!("tt{}_nh{}_w{}", i, j, k), *wc)?;
                }
            }
            // Neighbourhood types
            out.list_begin(&format!("tt{}_nhs", i))?;
            for (j, _) in data.nhtypes.iter().enumerate() {
                out.reference(&format!("tt{}_nh{}_wires", i, j))?;
            }
        }
        out.list_begin(&format!("chip_tts"))?;
        for (i, (_, data)) in self.types.iter().enumerate() {
            let num_bels = *tt_bel_count.get(i).unwrap();
            let num_pips = *tt_pip_count.get(i).unwrap();
            let num_wires = data.wires.len();
            let num_nhtypes = data.nhtypes.len();
            out.loc_type(
                num_bels,
                num_wires,
                num_pips,
                num_nhtypes,
                &format!("tt{}_bels", i),
                &format!("tt{}_wires", i),
                &format!("tt{}_pips", i),
                &format!("tt{}_nhs", i),
            )?;
        }
        Ok(())
    }
}
