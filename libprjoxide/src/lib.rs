use pyo3::prelude::*;
use pyo3::types::PySet;
use pyo3::wrap_pyfunction;

use std::fs::File;
use std::io::*;

#[macro_use]
extern crate lazy_static;

mod bitstream;
mod chip;
pub mod database;
pub mod fuzz;
mod wires;

#[pyclass]
struct Database {
    db: database::Database,
}

#[pymethods]
impl Database {
    #[new]
    pub fn __new__(obj: &PyRawObject, root: &str) {
        obj.init({
            Database {
                db: database::Database::new(root),
            }
        });
    }
}

#[pyclass]
struct Fuzzer {
    fz: fuzz::Fuzzer,
}

#[pymethods]
impl Fuzzer {
    #[staticmethod]
    pub fn word_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_tiles: &PySet,
        name: &str,
        width: usize,
        zero_bitfile: &str,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_word_fuzzer(
                &mut db.db,
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .unwrap()
                    .map(|x| x.unwrap().extract::<String>().unwrap())
                    .collect(),
                name,
                width,
                zero_bitfile,
            ),
        }
    }

    #[staticmethod]
    pub fn pip_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_tiles: &PySet,
        to_wire: &str,
        fixed_conn_tile: &str,
        full_mux: bool,
        skip_fixed: bool,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_pip_fuzzer(
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .unwrap()
                    .map(|x| x.unwrap().extract::<String>().unwrap())
                    .collect(),
                to_wire,
                fixed_conn_tile,
                full_mux,
                skip_fixed,
            ),
        }
    }

    #[staticmethod]
    pub fn enum_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_tiles: &PySet,
        name: &str,
        include_zeros: bool,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_enum_fuzzer(
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .unwrap()
                    .map(|x| x.unwrap().extract::<String>().unwrap())
                    .collect(),
                name,
                include_zeros,
            ),
        }
    }

    fn add_word_sample(&mut self, db: &mut Database, index: usize, base_bitfile: &str) {
        self.fz.add_word_sample(&mut db.db, index, base_bitfile);
    }

    fn add_pip_sample(&mut self, db: &mut Database, from_wire: &str, base_bitfile: &str) {
        self.fz.add_pip_sample(&mut db.db, from_wire, base_bitfile);
    }

    fn add_enum_sample(&mut self, db: &mut Database, option: &str, base_bitfile: &str) {
        self.fz.add_enum_sample(&mut db.db, option, base_bitfile);
    }

    fn solve(&mut self, db: &mut Database) {
        self.fz.solve(&mut db.db);
    }
}

#[pyclass]
struct Chip {
    c: chip::Chip,
}

#[pymethods]
impl Chip {
    #[new]
    pub fn __new__(obj: &PyRawObject, db: &mut Database, name: &str) {
        obj.init({
            Chip {
                c: chip::Chip::from_name(&mut db.db, name),
            }
        });
    }

    fn normalize_wire(&mut self, tile: &str, wire: &str) -> String {
        wires::normalize_wire(&self.c, self.c.tile_by_name(tile).unwrap(), wire)
    }
}

#[pyfunction]
fn parse_bitstream(d: &mut Database, file: &str) -> PyResult<()> {
    let mut f = File::open(file)?;
    let mut buffer = Vec::new();
    // read the whole file
    f.read_to_end(&mut buffer)?;
    let mut parser = bitstream::BitstreamParser::new(&buffer);
    let parse_result = parser.parse(&mut d.db);
    match parse_result {
        Err(x) => {
            println!("Parse error: {}", x);
            Ok(())
        }
        Ok(mut chip) => {
            chip.cram_to_tiles();
            chip.print(&mut std::io::stdout());
            Ok(())
        }
    }
}

#[pymodule]
fn libprjoxide(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(parse_bitstream))?;
    m.add_class::<Database>()?;
    m.add_class::<Fuzzer>()?;
    m.add_class::<Chip>()?;
    Ok(())
}
