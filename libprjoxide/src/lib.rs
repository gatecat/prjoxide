use pyo3::prelude::*;

mod bitstream;
mod chip;

#[pymodule]
fn pyprjoxide(py: Python, m: &PyModule) -> PyResult<()> {
    Ok(())
}
