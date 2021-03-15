use crate::chip::Chip;
use crate::database::Database;
use std::collections::HashMap;

use crate::bba::idstring::*;
use crate::bba::idxset::*;
use crate::bba::tiletype::TileTypes;


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
    key: TileTypeKey,
    wires: IndexedMap<IdString, IcWire>,
    pips: Vec<IcPip>,
    // TODO: constants, sites, etc
}

impl IcTileType {
    pub fn new(key: TileTypeKey) -> IcTileType {
        IcTileType {
            key: key,
            wires: IndexedMap::new(),
            pips: Vec::new(),
        }
    }
    pub fn wire(&mut self, name: IdString) -> usize {
        self.wires.add(&name, IcWire::new(name))
    }
}

pub struct IcWire {
    name: IdString,
    pips_uphill: Vec<usize>,
    pips_downhill: Vec<usize>,
}

impl IcWire {
    pub fn new(name: IdString) -> IcWire {
        IcWire {
            name: name,
            pips_uphill: Vec::new(),
            pips_downhill: Vec::new(),
        }
    }
}

pub struct IcPip {
    name: IdString,
    from_wire: usize,
    to_wire: usize,
}

// A tile instance
struct IcTileInst {
    x: u32,
    y: u32,
    type_idx: usize,
    // mapping between wires and nodes
    wire_to_node: Vec<usize>,
}

impl IcTileInst {
    pub fn new(x: u32, y: u32) -> IcTileInst {
        IcTileInst {
            x: x,
            y: y,
            type_idx: 0,
            wire_to_node: Vec::new(),
        }
    }
}

// A reference to a tile wire
pub struct IcWireRef {
    tile_idx: usize,
    wire_idx: usize,
}

// A node instance
struct IcNode {
    // list of tile wires in the node
    wires: Vec<IcWireRef>,
}

impl IcNode {
    pub fn new() -> IcNode {
        IcNode {
            wires: Vec::new(),
        }
    }
}

// The overall routing resource graph
pub struct IcGraph {
    tile_types: IndexedMap<TileTypeKey, IcTileType>,
    tiles: Vec<IcTileInst>,
    nodes: Vec<IcNode>,
    width: u32,
    height: u32,
}

impl IcGraph {
    pub fn new(width: u32, height: u32) -> IcGraph {
        IcGraph {
            tile_types: IndexedMap::new(),
            tiles: (0..width).zip(0..height).map(|(x, y)| IcTileInst::new(x, y)).collect(),
            nodes: Vec::new(),
            width: width,
            height: height
        }
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
            g: IcGraph::new(width, height),
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
            t.type_idx = self.g.tile_types.add(key, IcTileType::new(key.clone()));
        }
        for (key, lt) in self.g.tile_types.iter_mut() {
            // setup wires for all sub-tile-types
            for tt in key.tile_types.iter() {
                let tt_data = self.orig_tts.get(tt).unwrap();
                for wire in tt_data.wire_ids.iter() {
                    lt.wire(*wire);
                }
            }

        }
    }

    pub fn run(ids: &'a mut IdStringDB, chip: &'a Chip, db: &'a mut Database) -> IcGraph {
        let mut builder = GraphBuilder::new(ids, chip, db);
        builder.setup_tiletypes();
        builder.g
    }
}
