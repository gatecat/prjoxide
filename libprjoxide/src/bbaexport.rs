mod bba {
    pub mod idstring;
    pub mod idxset;
    pub mod tileloc;
    pub mod tiletype;
}
mod chip;
mod database;
use crate::bba::idstring::*;

fn main() {
    let mut ids = IdStringDB::new();
}
