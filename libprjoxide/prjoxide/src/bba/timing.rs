use std::collections::BTreeMap;
use crate::bba::idstring::*;
use crate::bba::idxset::IndexedSet;
use crate::bba::bbastruct::*;
use crate::database::*;

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
        // Sorting by IdString keys allows fast binary search lookups in nextpnr
        self.cell_types.sort_by(|a, b| (a.cell_type, a.cell_variant).partial_cmp(&(b.cell_type, b.cell_variant)).unwrap());
        self.cell_types.iter_mut().for_each(|x| x.sort());
    }
    pub fn import_cells(&mut self, family: &str, db: &mut Database, ids: &mut IdStringDB) {
        let data = db.cell_timing_db(family, &self.name);
        for (ct, c) in data.celltypes.iter() {
            // Use : as the delimiter between cell type and cell variant
            let split_type :Vec<&str> = ct.splitn(2, ':').collect();
            let cell_type = ids.id(split_type[0]);
            let cell_variant = ids.id(split_type.get(1).unwrap_or(&""));
            let mut bc = BBACellTiming::new(cell_type, cell_variant);
            // Iterate over and import delays and checks from the database
            for iopath in c.iopaths.iter() {
                bc.prop_delays.push(BBAPropDelay {
                    from_port: ids.id(&iopath.from_pin),
                    to_port :ids.id(&iopath.to_pin),
                    min_delay: iopath.minv,
                    max_delay: iopath.maxv,
                });
            }
            for setuphold in c.setupholds.iter() {
                bc.setup_holds.push(BBASetupHold {
                    sig_port: ids.id(&setuphold.pin),
                    clock_port: ids.id(&setuphold.clock),
                    min_setup: setuphold.min_setup,
                    max_setup: setuphold.max_setup,
                    min_hold: setuphold.min_hold,
                    max_hold: setuphold.max_hold,
                })
            }
            self.cell_types.push(bc);
        }
        self.sort();
    }
    pub fn import_pipclasses(&mut self, family: &str, db: &mut Database, pip_classes: &IndexedSet<String>) {
        let data = db.interconn_timing_db(family, &self.name);
        for (i, cls) in pip_classes.iter().enumerate() {
            if i == 0 {
                // Default class is added by default
                continue;
            }
            // Check we haven't got out of sync for some reason
            assert!(i == self.pip_classes.len());
            // Check if the class is actually in the database
            self.pip_classes.push(match data.pip_classes.get(cls) {
                Some(dlys) => BBAPipTiming {
                    min_delay: dlys.base.0,
                    max_delay: dlys.base.1,
                    min_fanout_adder: 0,
                    max_fanout_adder: 0,
                },
                None => BBAPipTiming {
                    // Defaults
                    min_delay: 50,
                    max_delay: 50,
                    min_fanout_adder: 0,
                    max_fanout_adder: 0,
                }
            });
        }
    }
    pub fn write_bba(&self, bba: &mut BBAStructs) -> std::io::Result<()> {
        // Cell timing
        for (i, cell) in self.cell_types.iter().enumerate() {
            bba.list_begin(&format!("sp{}_c{}_delays", &self.name, i))?;
            for dly in cell.prop_delays.iter() {
                bba.cell_prop_delay(
                    dly.from_port,
                    dly.to_port,
                    dly.min_delay,
                    dly.max_delay,
                )?;
            }
            bba.list_begin(&format!("sp{}_c{}_setupholds", &self.name, i))?;
            for dly in cell.setup_holds.iter() {
                bba.cell_setup_hold(
                    dly.sig_port,
                    dly.clock_port,
                    dly.min_setup,
                    dly.max_setup,
                    dly.min_hold,
                    dly.max_hold,
                )?;
            }
        }
        bba.list_begin(&format!("sp{}_celltypes", &self.name))?;
        for (i, cell) in self.cell_types.iter().enumerate() {
            bba.cell_timing(
                cell.cell_type,
                cell.cell_variant,
                cell.prop_delays.len(),
                cell.setup_holds.len(),
                &format!("sp{}_c{}_delays", &self.name, i),
                &format!("sp{}_c{}_setupholds", &self.name, i),
            )?;
        }
        bba.list_begin(&format!("sp{}_pip_classes", &self.name))?;
        for pip_class in self.pip_classes.iter() {
            bba.pip_timing(
                pip_class.min_delay,
                pip_class.max_delay,
                pip_class.min_fanout_adder,
                pip_class.max_fanout_adder,
            )?;
        }
        Ok(())
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
    pub fn import(&mut self, family: &str, db: &mut Database,  ids: &mut IdStringDB) {
        for speed in self.speed_grades.values_mut() {
            speed.import_cells(family, db, ids);
            speed.import_pipclasses(family, db, &self.pip_classes);
        }
    }
    pub fn write_bba(&self, bba: &mut BBAStructs) -> std::io::Result<()> {
        for speed in self.speed_grades.values() {
            speed.write_bba(bba)?;
        }
        bba.list_begin("speed_grades")?;
        for speed in self.speed_grades.values() {
            bba.speed_grade(
                &speed.name,
                speed.cell_types.len(),
                speed.pip_classes.len(),
                &format!("sp{}_celltypes", &speed.name),
                &format!("sp{}_pip_classes", &speed.name),
            )?;
        }
        Ok(())
    }
}
