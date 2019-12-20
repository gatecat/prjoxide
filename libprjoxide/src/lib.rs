use pyo3::prelude::*;

mod bitstream;
mod chip;
pub mod database;

#[pymodule]
fn pyprjoxide(py: Python, m: &PyModule) -> PyResult<()> {
    Ok(())
}
