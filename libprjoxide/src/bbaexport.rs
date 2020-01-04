mod bba {
    pub mod idstring;
    pub mod idxset;
    pub mod tileloc;
    pub mod tiletype;
}
mod chip;
mod database;
use crate::bba::idstring::*;
use crate::bba::tileloc::*;
use crate::bba::tiletype::*;
use std::iter::FromIterator;

use std::io::Result;

fn main() -> Result<()> {
    let mut ids = IdStringDB::new();
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());
    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let mut db = database::Database::new(db_path_str);
    let tts = TileTypes::new(&mut db, "LIFCL", "LIFCL-40");
    let empty_chip = chip::Chip::from_name(&mut db, "LIFCL-40");
    let mut lgrid = LocationGrid::new(&empty_chip, &tts);
    let mut lts = LocationTypes::from_locs(&mut lgrid);
    lts.import_wires(&mut ids, &tts);
    for y in 0..lgrid.height {
        for x in 0..lgrid.width {
            print!("{},", lgrid.get(x, y).unwrap().type_at_loc.unwrap());
        }
        println!("");
    }
    Ok(())
}
