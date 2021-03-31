use crate::database::*;
use crate::wires::*;
use crate::bels::*;

use std::collections::{BTreeSet, BTreeMap};
use std::fmt;

#[derive(Clone)]
pub struct SitePin {
    pub tile_wire: String,
    pub site_wire: String,
    pub dir: PinDir,
    pub bel_pin: usize,
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

#[derive(Clone)]
pub struct SiteRoutingBel {
    pub src_wires: Vec<String>,
    pub dst_wire: String,
}

impl fmt::Debug for SiteRoutingBel {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} <-- {{", &self.dst_wire)?;
        let mut first = true;
        for src in self.src_wires.iter() {
            if !first { write!(f, ", ")?; }
            write!(f, "{}", src)?;
            first = false;
        }
        write!(f, "}}")?;
        Ok(())
    }
}

#[derive(Clone)]
pub struct SiteBelPin {
    pub bel_name: String,
    pub pin_name: String,
    pub site_wire: String,
    pub dir: PinDir,
}

impl fmt::Debug for SiteBelPin {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} {} {}",
            &self.site_wire,
            match self.dir {
                PinDir::INPUT => "-->",
                PinDir::OUTPUT => "<--",
                PinDir::INOUT => "<->",
            },
            &self.pin_name
        )
    }
}

#[derive(Clone, Eq, PartialEq)]
pub enum SiteBelClass {
    BEL,
    RBEL,
    PORT,
}

#[derive(Clone)]
pub struct SiteBel {
    pub name: String,
    pub bel_type: String,
    pub bel_class: SiteBelClass,
    pub pins: Vec<usize>,
}

#[derive(Clone)]
pub struct SiteWire {
    pub name: String,
    pub bel_pins: Vec<usize>,
}

#[derive(Clone)]
pub struct SitePIP {
    pub in_pin: usize,
    pub out_pin: usize,
}

#[derive(Clone)]
pub struct Site {
    pub name: String,
    pub site_type: String,
    pub wires: Vec<SiteWire>,
    pub bel_pins: Vec<SiteBelPin>,
    pub pins: Vec<SitePin>,
    pub last_input_pin: usize,
    pub bels: Vec<SiteBel>,
    pub pips: Vec<SitePIP>,
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

fn flatten_wires(tiletype: &str, tiledata: &TileBitsDatabase) -> SiteWireMap {
    let mut m = SiteWireMap {
        wire2root: BTreeMap::new(),
        root2wires: BTreeMap::new(),
    };
    for (dst_wire, conns) in tiledata.conns.iter() {
        if !is_site_wire(tiletype, dst_wire) {
            continue;
        }
        for c in conns {
            let looked_up_src = m.lookup_wire(&c.from_wire);
            let looked_up_dst = m.lookup_wire(dst_wire);
            if compare_wire(&looked_up_src, &looked_up_dst) && is_site_wire(tiletype, &c.from_wire) {
                m.add_alias(&looked_up_src, &looked_up_dst);
            } else {
                m.add_alias(&looked_up_dst, &looked_up_src);
            }
        }
    }
    return m;
}

pub fn build_sites(tiletype: &str, tiledata: &TileBitsDatabase) -> Vec<Site> {
    let mut sites = Vec::new();
    if tiletype == "PLC" {
        // Logic sites are complicated, and require the inference of complex site routing
        let flat_wires = flatten_wires(tiletype, tiledata);
        let mut pins = Vec::new();
        let mut found_pins = BTreeSet::new();
        for (dst_wire, conns) in tiledata.conns.iter() {
            for conn in conns.iter() {
                if is_site_wire(tiletype, dst_wire) && !is_site_wire(tiletype, &conn.from_wire) {
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
                        bel_pin: 0,
                    });
                } else if !is_site_wire(tiletype, dst_wire) && is_site_wire(tiletype, &conn.from_wire) {
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
                        bel_pin: 0,
                    });
                }
            }
        }
        // For the F outputs where have a MUX/LUT choice; use the FF DI mux because it's not independently controllable from the FF mux
        for i in 0..4 {
                pins.push(SitePin {
                    tile_wire: format!("JF{}", 2*i),
                    site_wire: flat_wires.lookup_wire(&format!("JDI0_SLICE{}", &"ABCD"[i..i+1])),
                    dir: PinDir::OUTPUT,
                    bel_pin: 0,
                });
        }
        let mut site_bel_pins = Vec::new();
        let mut site_bels = Vec::new();
        let mut site_pips = Vec::new();
        // Import functional bels
        let orig_bels = get_tile_bels(&tiletype, tiledata);
        for orig_bel in orig_bels.iter() {
            let mut bel_pins = Vec::new();

            for pin in &orig_bel.pins {
                // TODO: relative X and Y coordinates
                let wire_name = pin.wire.rel_name(orig_bel.rel_x, orig_bel.rel_y);
                assert!(is_site_wire(tiletype, &wire_name));
                let site_wire = flat_wires.lookup_wire(&wire_name);
                bel_pins.push(site_bel_pins.len());
                site_bel_pins.push(SiteBelPin {
                    bel_name: orig_bel.name.clone(),
                    pin_name: pin.name.clone(),
                    site_wire: site_wire,
                    dir: pin.dir.clone(),
                });
            }

            site_bels.push(SiteBel {
                name: orig_bel.name.clone(),
                bel_class: SiteBelClass::BEL,
                bel_type: orig_bel.beltype.clone(),
                pins: bel_pins,
            });
        }
        // Convert pips to routing bels
        for (dst_wire, pips) in tiledata.pips.iter() {
            if !is_site_wire(tiletype, dst_wire) {
                continue;
            }
            let mut bel_pins = Vec::new();
            let site_dst_wire = flat_wires.lookup_wire(dst_wire);
            let bel_name = format!("RBEL_{}", site_dst_wire);
            let out_pin_idx = site_bel_pins.len();
            bel_pins.push(out_pin_idx);
            site_bel_pins.push(SiteBelPin {
                bel_name: bel_name.clone(),
                pin_name: site_dst_wire.clone(),
                site_wire: site_dst_wire.clone(),
                dir: PinDir::OUTPUT,
            });
            for src_wire in pips.iter().map(|p| &p.from_wire).filter(|w| is_site_wire(tiletype, w)).map(|w| flat_wires.lookup_wire(w)) {
                site_pips.push(SitePIP {
                    in_pin: site_bel_pins.len(),
                    out_pin: out_pin_idx,
                });
                bel_pins.push(site_bel_pins.len());
                site_bel_pins.push(SiteBelPin {
                    bel_name: bel_name.clone(),
                    pin_name: src_wire.clone(),
                    site_wire: src_wire.clone(),
                    dir: PinDir::INPUT,
                });
            }
            
            site_bels.push(SiteBel {
                name: bel_name.clone(),
                bel_class: SiteBelClass::RBEL,
                bel_type: bel_name.clone(),
                pins: bel_pins,
            });
        }
        // Create port bels
        for pin in pins.iter_mut() {
            let bel_name = pin.site_wire.clone();
            let bel_pins = vec![site_bel_pins.len()];
            pin.bel_pin = site_bel_pins.len();
            site_bel_pins.push(SiteBelPin {
                bel_name: bel_name.clone(),
                pin_name: pin.site_wire.clone(),
                site_wire: pin.site_wire.clone(),
                dir: match pin.dir {
                    PinDir::INPUT => PinDir::OUTPUT,
                    PinDir::OUTPUT => PinDir::INPUT,
                    PinDir::INOUT => PinDir::INOUT,
                }
            });
            site_bels.push(SiteBel {
                name: bel_name.clone(),
                bel_class: SiteBelClass::PORT,
                bel_type: bel_name.clone(),
                pins: bel_pins,
            })
        }

        let mut site_wire_to_pins = BTreeMap::new();
        for wire in flat_wires.root2wires.keys() {
            site_wire_to_pins.insert(wire, Vec::new());
        }
        for (i, bel_pin) in site_bel_pins.iter().enumerate() {
            site_wire_to_pins.entry(&bel_pin.site_wire).or_insert(Vec::new()).push(i)
        }

        let mut site_wires = Vec::new();
        for (wire, pins) in site_wire_to_pins.iter() {
            site_wires.push(SiteWire {
                name: wire.to_string(),
                bel_pins: pins.clone(),
            })
        }

        let mut shuffled_pins = Vec::new();
        shuffled_pins.extend(pins.iter().filter(|p| p.dir == PinDir::INPUT).cloned());
        let last_input_pin =  shuffled_pins.len() - 1;
        shuffled_pins.extend(pins.iter().filter(|p| p.dir != PinDir::INPUT).cloned());
        sites.push(Site {
            name: "PLC".to_string(),
            site_type: "PLC".to_string(),
            pins: shuffled_pins,
            last_input_pin: last_input_pin,
            wires: site_wires,
            bel_pins: site_bel_pins,
            bels: site_bels,
            pips: site_pips,
        });
    } else {
       for tile_bel in get_tile_bels(&tiletype, tiledata) {
            if tile_bel.beltype == "VCC_DRV" {
                continue;
            }
            // For everything else, just directly map bels onto sites
            // TODO: creating bels/pips for inversion, and sharing more code with the above path
            // TODO: inouts for top level ports?
            let mut pins = Vec::new();
            let mut site_bel_pins = Vec::new();
            let mut site_bels = Vec::new();

            for pin in tile_bel.pins.iter().filter(|p| p.dir != PinDir::INOUT) {
                let tile_wire = pin.wire.rel_name(tile_bel.rel_x, tile_bel.rel_y);
                pins.push(SitePin {
                    tile_wire: tile_wire,
                    site_wire: pin.name.clone(),
                    dir: pin.dir.clone(),
                    bel_pin: 0,
                });
            }
            // Create the site bel
            {
                let mut bel_pins = Vec::new();

                for pin in tile_bel.pins.iter() {
                    // TODO: relative X and Y coordinates
                    bel_pins.push(site_bel_pins.len());
                    site_bel_pins.push(SiteBelPin {
                        bel_name: tile_bel.name.clone(),
                        pin_name: pin.name.clone(),
                        site_wire: pin.name.clone(),
                        dir: pin.dir.clone(),
                    });
                }

                site_bels.push(SiteBel {
                    name: tile_bel.name.clone(),
                    bel_class: SiteBelClass::BEL,
                    bel_type: tile_bel.beltype.clone(),
                    pins: bel_pins,
                });
            }

            // Create notional pads for inout pins
            for pin in tile_bel.pins.iter().filter(|p| p.dir == PinDir::INOUT) {
                let bel_name = format!("PAD_{}", &pin.name);
                let bel_pins = vec![site_bel_pins.len()];
                site_bel_pins.push(SiteBelPin {
                    bel_name: bel_name.clone(),
                    pin_name: "PAD".to_string(),
                    site_wire: pin.name.clone(),
                    dir: PinDir::INOUT,
                });
                site_bels.push(SiteBel {
                    name: bel_name.clone(),
                    bel_class: SiteBelClass::BEL,
                    bel_type: "PAD".to_string(),
                    pins: bel_pins,
                })
            }

            // Create port bels
            for pin in pins.iter_mut() {
                let bel_name = pin.site_wire.clone();
                let bel_pins = vec![site_bel_pins.len()];
                pin.bel_pin = site_bel_pins.len();
                site_bel_pins.push(SiteBelPin {
                    bel_name: bel_name.clone(),
                    pin_name: pin.site_wire.clone(),
                    site_wire: pin.site_wire.clone(),
                    dir: match pin.dir {
                        PinDir::INPUT => PinDir::OUTPUT,
                        PinDir::OUTPUT => PinDir::INPUT,
                        PinDir::INOUT => PinDir::INOUT,
                    }
                });
                site_bels.push(SiteBel {
                    name: bel_name.clone(),
                    bel_class: SiteBelClass::PORT,
                    bel_type: bel_name.clone(),
                    pins: bel_pins,
                })
            }

            let mut site_wire_to_pins = BTreeMap::new();
            for (i, bel_pin) in site_bel_pins.iter().enumerate() {
                site_wire_to_pins.entry(&bel_pin.site_wire).or_insert(Vec::new()).push(i)
            }

            let mut site_wires = Vec::new();
            for (wire, pins) in site_wire_to_pins.iter() {
                site_wires.push(SiteWire {
                    name: wire.to_string(),
                    bel_pins: pins.clone(),
                })
            }

            let mut shuffled_pins = Vec::new();
            shuffled_pins.extend(pins.iter().filter(|p| p.dir == PinDir::INPUT).cloned());
            let last_input_pin =  shuffled_pins.len() - 1;
            shuffled_pins.extend(pins.iter().filter(|p| p.dir != PinDir::INPUT).cloned());
            sites.push(Site {
                name: tile_bel.name.to_string(),
                site_type: tile_bel.beltype.to_string(),
                pins: shuffled_pins,
                last_input_pin: last_input_pin,
                wires: site_wires,
                bel_pins: site_bel_pins,
                bels: site_bels,
                pips: Vec::new(),
            });

       }

    }
    return sites;
}
