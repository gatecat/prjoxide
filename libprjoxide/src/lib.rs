use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use std::fs::File;
use std::io::*;

mod bitstream;
mod chip;
pub mod database;

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
    Ok(())
}
