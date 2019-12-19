use pyo3::prelude::*;

mod bitstream;
mod database;

#[pymodule]
fn pyprjoxide(py: Python, m: &PyModule) -> PyResult<()> {
    Ok(())
}
