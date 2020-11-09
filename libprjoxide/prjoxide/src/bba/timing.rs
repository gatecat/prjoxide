use std::collections::BTreeMap;
use crate::bba::idstring::*;
use crate::bba::idxset::IndexedSet;


// Structures to represent imported timing data close to what we write out for nextpnr
pub struct BBAPropDelay {
    pub from_port: IdString,
    pub to_port: IdString,
    pub min_delay: i32,
    pub max_delay: i32,
}

pub struct BBASetupHold {
    pub sig_port: IdString,
    pub clock_port: IdString,
    pub min_setup: i32,
    pub max_setup: i32,
    pub min_hold: i32,
    pub max_hold: i32,
}

pub struct BBACellTiming {
    pub cell_type: IdString,
    pub cell_variant: IdString,
    pub prop_delays: Vec<BBAPropDelay>,
    pub setup_holds: Vec<BBASetupHold>,
}

impl BBACellTiming {
    pub fn new(cell_type: IdString, cell_variant: IdString) -> BBACellTiming {
        BBACellTiming {
            cell_type: cell_type,
            cell_variant: cell_variant,
            prop_delays: Vec::new(),
            setup_holds: Vec::new(),
        }
    }
    pub fn sort(&mut self) {
        self.prop_delays.sort_by(|a, b| (a.from_port, a.to_port).partial_cmp(&(b.from_port, b.to_port)).unwrap());
        self.setup_holds.sort_by(|a, b| (a.sig_port, a.clock_port).partial_cmp(&(b.sig_port, b.clock_port)).unwrap());
    }
}

pub struct BBAPipTiming {
    pub min_delay: i32,
    pub max_delay: i32,
    pub min_fanout_adder: i32,
    pub max_fanout_adder: i32,
}

pub struct BBASpeedGrade {
    pub name: String,
    pub cell_types: Vec<BBACellTiming>,
    pub pip_classes: Vec<BBAPipTiming>,
}

impl BBASpeedGrade {
    pub fn new(name: &str) -> BBASpeedGrade {
        BBASpeedGrade {
            name: name.to_string(),
            cell_types: Vec::new(),
            pip_classes: vec![
                // Implicit default pip class
                BBAPipTiming {
                    min_delay: 50,
                    max_delay: 50,
                    min_fanout_adder: 0,
                    max_fanout_adder: 0,
                }
            ]
        }
    }
    pub fn sort(&mut self) {
        self.cell_types.sort_by(|a, b| (a.cell_type, a.cell_variant).partial_cmp(&(b.cell_type, b.cell_variant)).unwrap());
    }
}

pub struct BBATiming {
    pub speed_grades: BTreeMap<String, BBASpeedGrade>,
    pub pip_classes: IndexedSet<String>,
}

impl BBATiming {
    pub fn new(speed_grades: &[&str]) -> BBATiming {
        let mut tmg = BBATiming {
            speed_grades: speed_grades.iter().map(|k| (k.to_string(), BBASpeedGrade::new(&k))).collect(),
            pip_classes: IndexedSet::new(),
        };
        // Default pip class
        tmg.pip_classes.add(&"default".to_string());
        return tmg;
    }
}
