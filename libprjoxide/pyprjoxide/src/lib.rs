use pyo3::prelude::*;
use pyo3::types::{PyList, PySet};
use pyo3::wrap_pyfunction;

use std::fs::File;
use std::io::*;
use std::collections::BTreeSet;

use prjoxide::bitstream;
use prjoxide::chip;
use prjoxide::database;
use prjoxide::database_html;
use prjoxide::docs;
use prjoxide::fuzz;
use prjoxide::ipfuzz;
use prjoxide::nodecheck;
use prjoxide::wires;
use prjoxide::pip_classes;
use prjoxide::sites;

#[pyclass]
struct Database {
    db: database::Database,
}

#[pymethods]
impl Database {
    #[new]
    pub fn __new__(root: &str) -> Self {
        Database {
            db: database::Database::new(root),
        }
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
        desc: &str,
        width: usize,
        zero_bitfile: &str,
        watched_bits: &PyList,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_word_fuzzer(
                &mut db.db,
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .map(|x| x.extract::<String>().unwrap())
                    .collect(),
                name,
                desc,
                width,
                zero_bitfile,
                &watched_bits.iter()
                .map(|x| x.extract::<(usize, usize)>().unwrap())
                .collect(),
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
        ignore_tiles: &PySet,
        full_mux: bool,
        skip_fixed: bool,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_pip_fuzzer(
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .map(|x| x.extract::<String>().unwrap())
                    .collect(),
                to_wire,
                fixed_conn_tile,
                &ignore_tiles
                    .iter()
                    .map(|x| x.extract::<String>().unwrap())
                    .collect(),
                full_mux,
                skip_fixed,
                &BTreeSet::new(),
            ),
        }
    }

    #[staticmethod]
    pub fn enum_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_tiles: &PySet,
        name: &str,
        desc: &str,
        include_zeros: bool,
        assume_zero_base: bool,
        watched_bits: &PyList,
    ) -> Fuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        Fuzzer {
            fz: fuzz::Fuzzer::init_enum_fuzzer(
                &base_chip,
                &fuzz_tiles
                    .iter()
                    .map(|x| x.extract::<String>().unwrap())
                    .collect(),
                name,
                desc,
                include_zeros,
                assume_zero_base,
                &watched_bits.iter()
                .map(|x| x.extract::<(usize, usize)>().unwrap())
                .collect(),
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
struct IPFuzzer {
    fz: ipfuzz::IPFuzzer,
}

#[pymethods]
impl IPFuzzer {
    #[staticmethod]
    pub fn word_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_ipcore: &str,
        fuzz_iptype: &str,
        name: &str,
        desc: &str,
        width: usize,
        inverted_mode: bool,
        watched_bits: &PyList,
    ) -> IPFuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        IPFuzzer {
            fz: ipfuzz::IPFuzzer::init_word_fuzzer(
                &mut db.db,
                &base_chip,
                fuzz_ipcore,
                fuzz_iptype,
                name,
                desc,
                width,
                inverted_mode,
                &watched_bits.iter()
                .map(|x| x.extract::<(u32, u8)>().unwrap())
                .collect(),
            ),
        }
    }

    #[staticmethod]
    pub fn enum_fuzzer(
        db: &mut Database,
        base_bitfile: &str,
        fuzz_ipcore: &str,
        fuzz_iptype: &str,
        name: &str,
        desc: &str,
        watched_bits: &PyList,
    ) -> IPFuzzer {
        let base_chip = bitstream::BitstreamParser::parse_file(&mut db.db, base_bitfile).unwrap();

        IPFuzzer {
            fz: ipfuzz::IPFuzzer::init_enum_fuzzer(
                &base_chip,
                fuzz_ipcore,
                fuzz_iptype,
                name,
                desc,
                &watched_bits.iter()
                .map(|x| x.extract::<(u32, u8)>().unwrap())
                .collect(),
            ),
        }
    }

    fn add_word_sample(&mut self, db: &mut Database, bits: &PyList, base_bitfile: &str) {
        self.fz.add_word_sample(
            &mut db.db,
            bits.iter().map(|x| x.extract::<bool>().unwrap()).collect(),
            base_bitfile,
        );
    }

    fn add_enum_sample(&mut self, db: &mut Database, option: &str, base_bitfile: &str) {
        self.fz.add_enum_sample(&mut db.db, option, base_bitfile);
    }

    fn solve(&mut self, db: &mut Database) {
        self.fz.solve(&mut db.db);
    }
}

#[pyfunction]
fn copy_db(
    db: &mut Database,
    fam: &str,
    from_tt: &str,
    to_tts: &PyList,
    mode: &str,
    pattern: &str,
) {
    fuzz::copy_db(
        &mut db.db,
        fam,
        from_tt,
        &to_tts
            .iter()
            .map(|x| x.extract::<String>().unwrap())
            .collect(),
        mode,
        pattern,
    );
}

#[pyfunction]
fn add_always_on_bits(db: &mut Database, empty_bitfile: &str) {
    let mut empty_chip = bitstream::BitstreamParser::parse_file(&mut db.db, empty_bitfile).unwrap();
    empty_chip.cram_to_tiles();
    fuzz::add_always_on_bits(&mut db.db, &empty_chip);
}

#[pyclass]
struct Chip {
    c: chip::Chip,
}

#[pymethods]
impl Chip {
    #[new]
    pub fn __new__(db: &mut Database, name: &str) -> Self {
        Chip {
            c: chip::Chip::from_name(&mut db.db, name),
        }
    }

    #[staticmethod]
    pub fn from_bitstream(db: &mut Database, filename: &str) -> Chip {
        let chip = bitstream::BitstreamParser::parse_file(&mut db.db, filename).unwrap();
        Chip { c: chip }
    }

    fn normalize_wire(&mut self, tile: &str, wire: &str) -> String {
        wires::normalize_wire(&self.c, self.c.tile_by_name(tile).unwrap(), wire)
    }

    fn get_ip_values(&mut self) -> Vec<(u32, u8)> {
        self.c.ipconfig.iter().map(|(a, d)| (*a, *d)).collect()
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

#[pyfunction]
fn write_tilegrid_html(d: &mut Database, family: &str, device: &str, file: &str) -> PyResult<()> {
    database_html::write_tilegrid_html(&mut d.db, family, device, file);
    Ok(())
}

#[pyfunction]
fn write_region_html(d: &mut Database, family: &str, device: &str, file: &str) -> PyResult<()> {
    database_html::write_region_html(&mut d.db, family, device, file);
    Ok(())
}

#[pyfunction]
fn check_nodes(d: &mut Database, device: &str, nodefile: &str) -> PyResult<()> {
    let c = chip::Chip::from_name(&mut d.db, device);
    nodecheck::check(&mut d.db, &c, nodefile);
    Ok(())
}

#[pyfunction]
fn build_sites(d: &mut Database, device: &str, tiletype: &str) -> PyResult<()> {
    let c = chip::Chip::from_name(&mut d.db, device);
    let tdb = d.db.tile_bitdb(&c.family, tiletype);
    sites::build_sites(tiletype, &tdb.db);
    Ok(())
}

#[pyfunction]
fn write_tilebits_html(
    d: &mut Database,
    docs_root: &str,
    family: &str,
    device: &str,
    tiletype: &str,
    file: &str,
) -> PyResult<()> {
    database_html::write_bits_html(&mut d.db, docs_root, family, device, tiletype, file);
    Ok(())
}

#[pyfunction]
fn md_file_to_html(filename: &str) -> String {
    docs::md_file_to_html(filename)
}

#[pyfunction]
fn classify_pip(src_x: i32, src_y: i32, src_name: &str, dst_x: i32, dst_y: i32, dst_name: &str) -> Option<String> {
    pip_classes::classify_pip(src_x, src_y, src_name, dst_x, dst_y, dst_name)
}

#[pymodule]
fn libpyprjoxide(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_wrapped(wrap_pyfunction!(parse_bitstream))?;
    m.add_wrapped(wrap_pyfunction!(write_tilegrid_html))?;
    m.add_wrapped(wrap_pyfunction!(write_region_html))?;
    m.add_wrapped(wrap_pyfunction!(write_tilebits_html))?;
    m.add_wrapped(wrap_pyfunction!(md_file_to_html))?;
    m.add_wrapped(wrap_pyfunction!(check_nodes))?;
    m.add_wrapped(wrap_pyfunction!(copy_db))?;
    m.add_wrapped(wrap_pyfunction!(add_always_on_bits))?;
    m.add_wrapped(wrap_pyfunction!(classify_pip))?;
    m.add_wrapped(wrap_pyfunction!(build_sites))?;
    m.add_class::<Database>()?;
    m.add_class::<Fuzzer>()?;
    m.add_class::<IPFuzzer>()?;
    m.add_class::<Chip>()?;
    Ok(())
}
