use crate::chip::Chip;
use crate::database::Database;
use std::collections::HashMap;

use crate::bba::idstring::*;


// A tile type from the interchange format perspective
// this is not the same as a database tile type; because the Oxide graph can have
// more than one tile at a grid location whereas the interchange grid is one tile
// per location

#[derive(Clone, Eq, PartialEq, Hash)]
struct TileTypeKey {
    pub tile_types: Vec<String>,
}
impl TileTypeKey {
    pub fn new() -> TileTypeKey {
        TileTypeKey { tile_types: Vec::new() }
    }
}

struct IcTileType {
    key: TileTypeKey,
    type_idx: u32,
    wires: Vec<IcWire>,
    pips: Vec<IcPip>,
    wires_by_name: HashMap<IdString, usize>,
    // TODO: constants, sites, etc
}

impl IcTileType {
    pub fn new(key: TileTypeKey, idx: u32) -> IcTileType {
        IcTileType {
            key: key,
            type_idx: idx,
            wires: Vec::new(),
            pips: Vec::new(),
            wires_by_name: HashMap::new(),
        }
    }
}

struct IcWire {
    name: IdString,
    pips_uphill: Vec<u32>,
    pips_downhill: Vec<u32>,
}

struct IcPip {
    name: IdString,
    from_wire: u32,
    to_wire: u32,
}

// A tile instance
struct IcTileInst {
    type_idx: u32,
    // mapping between wires and nodes
    wire_to_node: Vec<u32>,
}

impl IcTileInst {
    pub fn new() -> IcTileInst {
        IcTileInst {
            type_idx: 0,
            wire_to_node: Vec::new(),
        }
    }
}

// A reference to a tile wire
struct IcWireRef {
    tile_idx: u32,
    wire_idx: u32,
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
struct IcGraph {
    tile_types: Vec<IcTileType>,
    tiles: Vec<IcTileInst>,
    nodes: Vec<IcNode>,
    width: u32,
    height: u32,
}

impl IcGraph {
    pub fn new(width: u32, height: u32) -> IcGraph {
        IcGraph {
            tile_types: Vec::new(),
            tiles: (0..width*height).map(|_| IcTileInst::new()).collect(),
            nodes: Vec::new(),
            width: width,
            height: height
        }
    }
}

struct GraphBuilder<'a> {
    g: IcGraph,
    ids: &'a mut IdStringDB,
    chip: &'a Chip,
    db: &'a mut Database,
    tiletypes_by_xy: HashMap<(u32, u32), TileTypeKey>,
}


impl <'a> GraphBuilder<'a> {
    pub fn new(ids: &'a mut IdStringDB, chip: &'a Chip, db: &'a mut Database) -> GraphBuilder<'a> {
        let mut width = 0;
        let mut height = 0;
        let mut tiletypes_by_xy = HashMap::new();
        for t in chip.tiles.iter() {
            tiletypes_by_xy.entry((t.x, t.y)).or_insert(TileTypeKey::new()).tile_types.push(t.tiletype.to_string());
            width = std::cmp::max(width, t.x + 1);
            height = std::cmp::max(height, t.y + 1);
        }

        GraphBuilder {
            g: IcGraph::new(width, height),
            ids: ids,
            chip: chip,
            db: db,
            tiletypes_by_xy: tiletypes_by_xy,
        }
    }

}
