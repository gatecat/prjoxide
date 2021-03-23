#![cfg(feature = "interchange")]

use crate::chip::Chip;
use crate::database::Database;
use std::collections::{HashSet, HashMap};

use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::{Neighbour, TileTypes};

use crate::sites::*;
use crate::wires::*;

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
    pub fn add_pip(&mut self, src: IdString, dst: IdString) {
        let src_idx = self.wire(src);
        let dst_idx = self.wire(dst);
        self.pips.push(IcPip {
            src_wire: src_idx,
            dst_wire: dst_idx,
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

pub struct IcPip {
    pub src_wire: usize,
    pub dst_wire: usize,
}

// A tile instance
pub struct IcTileInst {
    pub name: IdString,
    pub x: u32,
    pub y: u32,
    pub type_idx: usize,
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

// A node instance
pub struct IcNode {
    // list of tile wires in the node
    pub wires: HashSet<IcWireRef>,
    pub root_wire: IcWireRef,
}

impl IcNode {
    pub fn new(root_wire: IcWireRef) -> IcNode {
        IcNode {
            wires: [root_wire.clone()].iter().cloned().collect(),
            root_wire: root_wire,
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
}

impl IcGraph {
    pub fn new(ids: &mut IdStringDB, width: u32, height: u32) -> IcGraph {
        IcGraph {
            tile_types: IndexedMap::new(),
            tiles: (0..width*height).map(|i| IcTileInst::new(ids, i%width, i/width)).collect(),
            nodes: Vec::new(),
            width: width,
            height: height
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
    pub fn map_node(&mut self, root_x: u32, root_y: u32, root_wire: IdString, wire_x: u32, wire_y: u32, wire: IdString) {
        // Make sure wire exists in both tiles
        self.type_at(root_x, root_y).wire(root_wire);
        self.type_at(wire_x, wire_y).wire(wire);
        // Update wire-node mapping
        let root_tile_idx = self.tile_idx(root_x, root_y);
        let node_idx = match self.tiles[root_tile_idx].wire_to_node.get(&root_wire) {
            Some(i) => *i,
            None => {
                let idx = self.nodes.len();
                self.nodes.push(IcNode::new(IcWireRef { tile_name: self.tiles[root_tile_idx].name, wire_name: root_wire }));
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

        let orig_tts = TileTypes::new(db, ids, &chip.family, &[&chip.device]);

        GraphBuilder {
            g: IcGraph::new(ids, width, height),
            ids: ids,
            chip: chip,
            db: db,
            tiletypes_by_xy: tiletypes_by_xy,
            // the original tiletypes from the database
            orig_tts: orig_tts,
        }
    }
    fn setup_tiletypes(&mut self) {
        for t in self.g.tiles.iter_mut() {
            let key = self.tiletypes_by_xy.get(&(t.x, t.y)).unwrap();
            t.type_idx = self.g.tile_types.add(key, IcTileType::new(key.clone(), &self.chip.family, self.db));
        }
        for (key, lt) in self.g.tile_types.iter_mut() {
            // setup wires for site pins
            let site_wires : Vec<String> = lt.site_types.iter().map(|s| s.pins.iter()).flatten().map(|p| p.tile_wire.clone()).collect();
            for w in site_wires {
                lt.wire(self.ids.id(&w));
            }
            for tt in key.tile_types.iter() {
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
                        lt.add_pip(self.ids.id(&pip.from_wire), self.ids.id(to_wire));
                    }
                }
                for (to_wire, conns) in tdb.conns.iter() {
                    for conn in conns.iter() {
                        if is_site_wire(tt, &conn.from_wire) && is_site_wire(tt, to_wire) {
                            continue;
                        }
                        lt.add_pip(self.ids.id(&conn.from_wire), self.ids.id(to_wire));
                    }
                }
            }
        }
    }
    // Convert a neighbour to a coordinate
    pub fn neighbour_tile(&self, x: u32, y: u32, n: &Neighbour) -> Option<(u32, u32)> {
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
            // TODO: globals
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
                            self.g.map_node(root_x, root_y, self.ids.id(base_wire), *x, *y, self.ids.id(wire));
                        }

                    } else {
                        // root node, map to itself
                        self.g.map_node(*x, *y, self.ids.id(base_wire), *x, *y, self.ids.id(base_wire));
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
