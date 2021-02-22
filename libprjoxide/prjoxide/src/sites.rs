use crate::chip::*;
use crate::database::*;
use crate::wires::*;
use crate::bels::*;

use std::collections::{BTreeSet, BTreeMap};
use std::fmt;

pub struct SitePin {
    pub tile_wire: String,
    pub site_wire: String,
    pub dir: PinDir,
}

impl fmt::Debug for SitePin {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} {} {}",
            &self.tile_wire,
            match self.dir {
                PinDir::INPUT => "-->",
                PinDir::OUTPUT => "<--",
                PinDir::INOUT => "<->",
            },
            &self.site_wire
        )
    }
}

pub struct SitePip {
    pub src_wire: String,
    pub dst_wire: String,
}

pub struct Site {
    pub name: String,
    pub pins: Vec<SitePin>,
    pub pips: Vec<SitePip>,
}

// To speed up site routing; where fixed connections connect multiple site wires together, merge them into one
// this structure stores the mapping in both directions
struct SiteWireMap {
    pub wire2root: BTreeMap<String, String>,
    pub root2wires: BTreeMap<String, BTreeSet<String>>,
}

impl SiteWireMap {
    pub fn lookup_wire(&self, name: &str) -> String {
        self.wire2root.get(name).unwrap_or(&name.to_string()).to_string()
    }
    pub fn add_alias(&mut self, root: &str, wire: &str) {
        self.wire2root.entry(wire.to_string()).or_insert(root.to_string());
        self.root2wires.entry(root.to_string()).or_insert(BTreeSet::new()).insert(wire.to_string());
        if let Some(wires) = self.root2wires.get(wire).cloned() {
            for w in wires {
                *self.wire2root.get_mut(&w).unwrap() = root.to_string();
                self.root2wires.get_mut(root).unwrap().insert(w.to_string());
            }
            self.root2wires.remove(wire);
        }
    }
}

// determine which wire has priority when flattening connections
fn compare_wire(a: &str, b: &str) -> bool {
    // prioritise shorter wires first, then fall back to a lexicographical compare
    (a.len(), a) < (b.len(), b)
}

fn flatten_wires(tile: &Tile, tiledata: &TileBitsDatabase) -> SiteWireMap {
    let mut m = SiteWireMap {
        wire2root: BTreeMap::new(),
        root2wires: BTreeMap::new(),
    };
    for (dst_wire, conns) in tiledata.conns.iter() {
        if !is_site_wire(tile, dst_wire) {
            continue;
        }
        for c in conns {
            let looked_up_src = m.lookup_wire(&c.from_wire);
            let looked_up_dst = m.lookup_wire(dst_wire);
            if compare_wire(&looked_up_src, &looked_up_dst) && is_site_wire(tile, &c.from_wire) {
                m.add_alias(&looked_up_src, &looked_up_dst);
            } else {
                m.add_alias(&looked_up_dst, &looked_up_src);
            }
        }
    }
    return m;
}

pub fn build_sites(_chip: &Chip, tile: &Tile, tiledata: &TileBitsDatabase) {
    let flat_wires = flatten_wires(tile, tiledata);
    let mut pins = Vec::new();
    let mut found_pins = BTreeSet::new();
    for (dst_wire, conns) in tiledata.conns.iter() {
        for conn in conns.iter() {
            if is_site_wire(tile, dst_wire) && !is_site_wire(tile, &conn.from_wire) {
                // from tile into site
                let site_dst_wire = flat_wires.lookup_wire(dst_wire);
                if found_pins.contains(&(conn.from_wire.to_string(), site_dst_wire.to_string())) {
                    continue;
                }
                found_pins.insert((conn.from_wire.to_string(), site_dst_wire.to_string()));
                pins.push(SitePin {
                    tile_wire: conn.from_wire.clone(),
                    site_wire: site_dst_wire,
                    dir: PinDir::INPUT,
                });
            } else if !is_site_wire(tile, dst_wire) && is_site_wire(tile, &conn.from_wire) {
                // from site into tile
                let site_src_wire = flat_wires.lookup_wire(&conn.from_wire);
                if found_pins.contains(&(site_src_wire.to_string(), dst_wire.to_string())) {
                    continue;
                }
                found_pins.insert((site_src_wire.to_string(), dst_wire.to_string()));
                pins.push(SitePin {
                    tile_wire: dst_wire.to_string(),
                    site_wire: site_src_wire,
                    dir: PinDir::OUTPUT,
                });
            }
        }
    }
    for pin in pins.iter() {
        println!("{:?}", pin);
    }
}
