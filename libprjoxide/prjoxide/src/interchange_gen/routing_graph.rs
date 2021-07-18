#![cfg(feature = "interchange")]

use crate::chip::Chip;
use crate::database::{Database, DeviceGlobalsData,};
use std::collections::{HashSet, HashMap};
use std::convert::TryInto;

use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::{Neighbour, BranchSide, TileTypes};

use crate::sites::*;
use crate::wires::*;
use crate::pip_classes::classify_pip;

// A tile type from the interchange format perspective
// this is not the same as a database tile type; because the Oxide graph can have
// more than one tile at a grid location whereas the interchange grid is one tile
// per location

#[derive(Clone, Eq, PartialEq, Hash)]
pub struct TileTypeKey {
    pub tile_types: Vec<String>,
}
impl TileTypeKey {
    pub fn new() -> TileTypeKey {
        TileTypeKey { tile_types: Vec::new() }
    }
}

pub struct IcTileType {
    pub key: TileTypeKey,
    pub wires: IndexedMap<IdString, IcWire>,
    pub pips: Vec<IcPip>,
    pub site_types: Vec<Site>,
    // TODO: constants, sites, etc
}

impl IcTileType {
    pub fn new(key: TileTypeKey, family: &str, db: &mut Database) -> IcTileType {
        let mut site_types = Vec::new();
        for tt in key.tile_types.iter() {
            site_types.extend(build_sites(&tt, &db.tile_bitdb(family, &tt).db));
        }
        IcTileType {
            key: key,
            wires: IndexedMap::new(),
            pips: Vec::new(),
            site_types: site_types,
        }
    }
    pub fn wire(&mut self, name: IdString) -> usize {
        self.wires.add(&name, IcWire::new(name))
    }
    pub fn add_pip(&mut self, sub_tile: usize, src: IdString, dst: IdString, tmg_idx: usize) {
        let src_idx = self.wire(src);
        let dst_idx = self.wire(dst);
        self.pips.push(IcPip {
            src_wire: src_idx,
            dst_wire: dst_idx,
            sub_tile: sub_tile,
            pseudo_cells: Vec::new(),
            tmg_idx: tmg_idx,
        });
    }
    pub fn add_ppip(&mut self, sub_tile: usize, src: IdString, dst: IdString, tmg_idx: usize, pseudo_cells: Vec<IcPseudoCell>) {
        let src_idx = self.wire(src);
        let dst_idx = self.wire(dst);
        self.pips.push(IcPip {
            src_wire: src_idx,
            dst_wire: dst_idx,
            sub_tile: sub_tile,
            pseudo_cells: pseudo_cells,
            tmg_idx: tmg_idx,
        });
    }
}

pub struct IcWire {
    pub name: IdString,
}

impl IcWire {
    pub fn new(name: IdString) -> IcWire {
        IcWire {
            name: name,
        }
    }
}

pub struct IcPseudoCell {
    pub bel: IdString,
    pub pins: Vec<IdString>,
}

pub struct IcPip {
    pub src_wire: usize,
    pub dst_wire: usize,
    pub sub_tile: usize,
    pub pseudo_cells: Vec<IcPseudoCell>,
    pub tmg_idx: usize,
}

// A tile instance
pub struct IcTileInst {
    pub name: IdString,
    pub x: u32,
    pub y: u32,
    pub type_idx: usize,
    pub key: TileTypeKey,
    // mapping between wires and nodes
    wire_to_node: HashMap<IdString, usize>,
}

impl IcTileInst {
    pub fn new(ids: &mut IdStringDB, x: u32, y: u32) -> IcTileInst {
        IcTileInst {
            name: ids.id(&format!("R{}C{}", y, x)),
            x: x,
            y: y,
            type_idx: 0,
            key: TileTypeKey::new(),
            wire_to_node: HashMap::new(),
        }
    }
}

// A reference to a tile wire
#[derive(Clone, Hash, Eq, PartialEq)]
pub struct IcWireRef {
    pub tile_name: IdString,
    pub wire_name: IdString,
}

pub const WIRE_TYPE_GENERAL: u32 = 0;
pub const WIRE_TYPE_SPECIAL: u32 = 1;
pub const WIRE_TYPE_GLOBAL: u32 = 2;


// A node instance
pub struct IcNode {
    // list of tile wires in the node
    pub wires: HashSet<IcWireRef>,
    pub root_wire: IcWireRef,
    pub wire_type: u32,
}

impl IcNode {
    pub fn new(root_wire: IcWireRef, wire_type: u32) -> IcNode {
        IcNode {
            wires: [root_wire.clone()].iter().cloned().collect(),
            root_wire: root_wire,
            wire_type: wire_type,
        }
    }
}

// The overall routing resource graph
pub struct IcGraph {
    pub tile_types: IndexedMap<TileTypeKey, IcTileType>,
    pub tiles: Vec<IcTileInst>,
    pub nodes: Vec<IcNode>,
    pub width: u32,
    pub height: u32,
    pub pip_timings: IndexedSet<String>,
}

impl IcGraph {
    pub fn new(ids: &mut IdStringDB, width: u32, height: u32) -> IcGraph {
        IcGraph {
            tile_types: IndexedMap::new(),
            tiles: (0..width*height).map(|i| IcTileInst::new(ids, i%width, i/width)).collect(),
            nodes: Vec::new(),
            width: width,
            height: height,
            pip_timings: IndexedSet::new(),
        }
    }
    pub fn tile_idx(&self, x: u32, y: u32) -> usize {
        assert!(x < self.width);
        assert!(y < self.height);
        ((y * self.width) + x) as usize
    }
    pub fn tile_at(&mut self, x: u32, y: u32) -> &mut IcTileInst {
        let idx = self.tile_idx(x, y);
        &mut self.tiles[idx]
    }
    pub fn type_at(&mut self, x: u32, y: u32) -> &mut IcTileType {
        let idx = self.tile_at(x, y).type_idx;
        self.tile_types.value_mut(idx)
    }
    pub fn map_node(&mut self, ids: &IdStringDB, root_x: u32, root_y: u32, root_wire: IdString, wire_x: u32, wire_y: u32, wire: IdString) {
        // Make sure wire exists in both tiles
        self.type_at(root_x, root_y).wire(root_wire);
        self.type_at(wire_x, wire_y).wire(wire);
        // Update wire-node mapping
        let root_tile_idx = self.tile_idx(root_x, root_y);
        let node_idx = match self.tiles[root_tile_idx].wire_to_node.get(&root_wire) {
            Some(i) => *i,
            None => {
                let idx = self.nodes.len();
                let wire_name_str = ids.str(root_wire);
                let wire_type = if wire_name_str.starts_with("H0") || wire_name_str.starts_with("V0") {
                    WIRE_TYPE_GENERAL
                } else if wire_name_str.starts_with("HPBX") || wire_name_str.starts_with("VPSX0") || wire_name_str.starts_with("HPRX0") {
                    WIRE_TYPE_GLOBAL
                } else {
                    WIRE_TYPE_SPECIAL
                };
                self.nodes.push(IcNode::new(IcWireRef { tile_name: self.tiles[root_tile_idx].name, wire_name: root_wire }, wire_type));
                self.tiles[root_tile_idx].wire_to_node.insert(root_wire, idx);
                idx
            }
        };
        let wire_tile_idx = self.tile_idx(wire_x, wire_y);
        self.nodes[node_idx].wires.insert(IcWireRef {tile_name: self.tiles[wire_tile_idx].name, wire_name: wire });
        self.tiles[wire_tile_idx].wire_to_node.insert(wire, node_idx);
    }
}

pub struct GraphBuilder<'a> {
    g: IcGraph,
    ids: &'a mut IdStringDB,
    chip: &'a Chip,
    glb: DeviceGlobalsData,
    db: &'a mut Database,
    tiletypes_by_xy: HashMap<(u32, u32), TileTypeKey>,
    orig_tts: TileTypes,
}


impl <'a> GraphBuilder<'a> {
    fn new(ids: &'a mut IdStringDB, chip: &'a Chip, db: &'a mut Database) -> GraphBuilder<'a> {
        let mut width = 0;
        let mut height = 0;
        let mut tiletypes_by_xy = HashMap::new();
        for t in chip.tiles.iter() {
            tiletypes_by_xy.entry((t.x, t.y)).or_insert(TileTypeKey::new()).tile_types.push(t.tiletype.to_string());
            width = std::cmp::max(width, t.x + 1);
            height = std::cmp::max(height, t.y + 1);
        }
        for v in tiletypes_by_xy.values_mut() {
            v.tile_types.sort();
        }

        let orig_tts = TileTypes::new(db, ids, &chip.family, &[&chip.device]);

        let globals = db.device_globals(&chip.family, &chip.device);

        GraphBuilder {
            g: IcGraph::new(ids, width, height),
            ids: ids,
            chip: chip,
            glb: globals.clone(),
            db: db,
            tiletypes_by_xy: tiletypes_by_xy,
            // the original tiletypes from the database
            orig_tts: orig_tts,
        }
    }

    fn get_pip_tmg_class(from_wire: &str, to_wire: &str) -> String {
        let (src_rel, src_name) = Neighbour::parse_wire(from_wire);
        let (dst_rel, dst_name) = Neighbour::parse_wire(to_wire);
        let (src_x, src_y) = match src_rel {
            Some(Neighbour::RelXY { rel_x: x, rel_y: y }) => (x, y),
            _ => (0, 0)
        };
        let (dst_x, dst_y) = match dst_rel {
            Some(Neighbour::RelXY { rel_x: x, rel_y: y }) => (x, y),
            _ => (0, 0)
        };
        classify_pip(src_x, src_y, src_name, dst_x, dst_y, dst_name)
            .unwrap_or("".into())
    }

    fn setup_tiletypes(&mut self) {
        for t in self.g.tiles.iter_mut() {
            let key = self.tiletypes_by_xy.get(&(t.x, t.y)).unwrap();
            t.key = key.clone();
            t.type_idx = self.g.tile_types.add(key, IcTileType::new(key.clone(), &self.chip.family, self.db));
        }
        let mut pip_timings = IndexedSet::new();
        for (key, lt) in self.g.tile_types.iter_mut() {
            // setup wires for site pins
            let site_wires : Vec<String> = lt.site_types.iter().map(|s| s.pins.iter()).flatten().map(|p| p.tile_wire.clone()).collect();
            for w in site_wires {
                lt.wire(self.ids.id(&w));
            }
            for (sub_tile, tt) in key.tile_types.iter().enumerate() {
                // setup wires for all sub-tile-types
                let tt_data = self.orig_tts.get(tt).unwrap();
                for wire in tt_data.wire_ids.iter() {
                    lt.wire(*wire);
                }
                // setup pips, both fixed and not
                // TODO: skip site wires and pips and deal with these later
                let tdb = &self.db.tile_bitdb(&self.chip.family, tt).db;
                for (to_wire, pips) in tdb.pips.iter() {
                    for pip in pips.iter() {
                        if is_site_wire(tt, &pip.from_wire) && is_site_wire(tt, to_wire) {
                            continue;
                        }
                        if to_wire.contains("CIBMUX") && pip.from_wire.contains("CIBMUX")
                            && to_wire.chars().rev().nth(1).unwrap() != pip.from_wire.chars().rev().nth(1).unwrap() {
                            // Don't use CIBMUX other than straight-through
                            // This avoids issues with having to carefully set CIBMUX for unused pins so they float high correctly, see 
                            // https://github.com/YosysHQ/nextpnr/blob/24ae205f20f0e1a0326e48002ab14d5bacfca1ef/nexus/fasm.cc#L272-L286
                            continue;
                        }
                        let tmg_cls = Self::get_pip_tmg_class(&pip.from_wire, to_wire);
                        let tmg_idx = pip_timings.add(&tmg_cls);
                        lt.add_pip(sub_tile, self.ids.id(&pip.from_wire), self.ids.id(to_wire), tmg_idx);
                    }
                }
                for (to_wire, conns) in tdb.conns.iter() {
                    for conn in conns.iter() {
                        if is_site_wire(tt, &conn.from_wire) && is_site_wire(tt, to_wire) {
                            continue;
                        }
                        lt.add_pip(sub_tile, self.ids.id(&conn.from_wire), self.ids.id(to_wire), 0);
                    }
                }
            }
            if lt.site_types.iter().find(|s| s.site_type == "PLC").is_some() {
                let gnd_wire = self.ids.id("G:GND");
                lt.wire(gnd_wire);
                let sub_tile = key.tile_types.iter().position(|x| &x[..] == "PLC").unwrap();
                for i in 0..8 {
                    // Create pseudo-ground drivers for LUT outputs
                    lt.add_ppip(sub_tile, gnd_wire, self.ids.id(&format!("JF{}", i)), 0,
                        vec![
                            IcPseudoCell {
                                bel: self.ids.id(&format!("SLICE{}_LUT{}", &"ABCD"[(i/2)..(i/2)+1], i%2)),
                                pins: vec![self.ids.id("F")],
                            }
                        ]);
                    // Create LUT route-through PIPs
                    for j in &["A", "B", "C", "D"] {
                        lt.add_ppip(sub_tile, self.ids.id(&format!("J{}{}", j, i)), self.ids.id(&format!("JF{}", i)), 0,
                        vec![
                            IcPseudoCell {
                                bel: self.ids.id(&format!("SLICE{}_LUT{}", &"ABCD"[(i/2)..(i/2)+1], i%2)),
                                pins: vec![self.ids.id(j), self.ids.id("F")],
                            }
                        ]);
                    }
                }
            }
        }
        self.g.pip_timings = pip_timings;
    }
    // Convert a neighbour to a coordinate
    pub fn neighbour_tile(&self, x: u32, y: u32, n: &Neighbour) -> Option<(u32, u32)> {
        let conv_tuple = |(x, y)| (x as u32, y as u32);
        match n {
            Neighbour::RelXY { rel_x, rel_y } => {
                let nx = (x as i32) + rel_x;
                let ny = (y as i32) + rel_y;
                if nx >= 0 && ny >= 0 && (nx as u32) < self.g.width && (ny as u32) < self.g.height {
                    Some((nx as u32, ny as u32))
                } else {
                    None
                }
            }
            Neighbour::Global => {
                // FIXME: current interchange format assumption that (0, 0) is empty
                Some((1, 1))
            }
            Neighbour::Branch => {
                let branch_col = self.glb.branch_sink_to_origin(x as usize).unwrap();
                Some((branch_col.try_into().unwrap(), y))
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
                Some((branch_col.try_into().unwrap(), y))
            }
            Neighbour::Spine => Some(conv_tuple(self.glb.spine_sink_to_origin(x as usize, y as usize).unwrap())),
            Neighbour::HRow => Some(conv_tuple(self.glb.hrow_sink_to_origin(x as usize, y as usize).unwrap())),
            _ => None
        }
    }
    fn setup_wire2node(&mut self) {
        for ((x, y), key) in self.tiletypes_by_xy.iter() {
            for tt in key.tile_types.iter() {
                for wire in self.orig_tts.get(tt).unwrap().wires.iter() {
                    let (neigh, base_wire) = Neighbour::parse_wire(wire);
                    if let Some(neigh) = neigh {
                        // it's a neighbour wire, map to the base tile
                        if let Some((root_x, root_y)) = self.neighbour_tile(*x, *y, &neigh) {
                            let base_wire_id = self.ids.id(base_wire);
                            let wire_id = self.ids.id(wire);
                            self.g.map_node(self.ids, root_x, root_y, base_wire_id, *x, *y, wire_id);
                        }

                    } else {
                        // root node, map to itself
                        let base_wire_id = self.ids.id(base_wire);
                        self.g.map_node(self.ids, *x, *y, base_wire_id, *x, *y, base_wire_id);
                    }
                }
            }
        }
    }

    pub fn run(ids: &'a mut IdStringDB, chip: &'a Chip, db: &'a mut Database) -> IcGraph {
        let mut builder = GraphBuilder::new(ids, chip, db);
        builder.setup_tiletypes();
        builder.setup_wire2node();
        builder.g
    }
}
