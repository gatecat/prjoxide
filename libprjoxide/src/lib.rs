use pyo3::prelude::*;

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

#[pymodule]
fn libprjoxide(py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<Database>()?;
    Ok(())
}
