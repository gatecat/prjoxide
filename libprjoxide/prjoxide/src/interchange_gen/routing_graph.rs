use std::collections::HashMap;

use crate::bba::idstring::*;


// A tile type from the interchange format perspective
// this is not the same as a database tile type; because the Oxide graph can have
// more than one tile at a grid location whereas the interchange grid is one tile
// per location
struct IcTileType {
	type_idx: u32,
	tile_types: Vec<String>,
	wires: Vec<IcWire>,
	pips: Vec<IcPip>,
	wires_by_name: HashMap<IdString, usize>,
	// TODO: constants, sites, etc
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

// The overall routing resource graph
struct IcGraph {
	tile_types: Vec<IcTileType>,
	tiles: Vec<IcTileInst>,
	nodes: Vec<IcNode>,
}