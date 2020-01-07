mod bba {
    pub mod bbafile;
    pub mod bbastruct;
    pub mod idstring;
    pub mod idxset;
    pub mod tileloc;
    pub mod tiletype;
}
mod bels;
mod chip;
mod database;
use crate::bba::bbastruct::*;
use crate::bba::idstring::*;
use crate::bba::tileloc::*;
use crate::bba::tiletype::*;
use std::iter::FromIterator;

use std::io::{BufWriter, Result};

fn main() -> Result<()> {
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());
    let mut ids = IdStringDB::from_constids(&args[1])?;
    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let mut db = database::Database::new(db_path_str);
    let tts = TileTypes::new(&mut db, &mut ids, "LIFCL", "LIFCL-40");
    let empty_chip = chip::Chip::from_name(&mut db, "LIFCL-40");
    let mut lgrid = LocationGrid::new(&empty_chip, &tts);
    lgrid.stamp_neighbours();
    let mut lts = LocationTypes::from_locs(&mut lgrid);
    lts.import_wires(&mut ids, &tts);
    /*
    for y in 0..lgrid.height {
        for x in 0..lgrid.width {
            print!("{},", lgrid.get(x, y).unwrap().type_at_loc.unwrap());
        }
        println!("");
    }
    */
    let mut bba_str = BufWriter::new(std::io::stdout());
    let mut bba = bba::bbafile::BBAWriter::new(&mut bba_str);
    bba.pre("#include \"nextpnr.h\"")?;
    bba.pre("NEXTPNR_NAMESPACE_BEGIN")?;
    bba.post("NEXTPNR_NAMESPACE_END")?;
    bba.push("db_blob")?;
    bba.ref_label("db")?;

    let mut bba_s = bba::bbastruct::BBAStructs::new(&mut bba);
    lts.write_locs_bba(&mut bba_s, &mut ids, &tts)?;
    lgrid.write_grid_bba(&mut bba_s, 0, &mut ids, &empty_chip)?;
    bba_s.list_begin("chips")?;
    lgrid.write_chip_bba(&mut bba_s, 0, &empty_chip)?;
    ids.write_bba(&mut bba_s)?;
    bba_s.list_begin("db")?;
    bba_s.database(1, "LIFCL", "chips", lts.types.len(), "chip_tts")?;

    bba_s.out.pop()?;

    Ok(())
}
