use prjoxide::bba::bbafile::*;
use prjoxide::bba::bbastruct::*;
use prjoxide::bba::idstring::*;
use prjoxide::bba::tileloc::*;
use prjoxide::bba::tiletype::*;
use prjoxide::chip::*;
use prjoxide::database::*;

use std::iter::FromIterator;

use std::fs::File;

use std::io::{BufWriter, Result};

fn main() -> Result<()> {
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());

    if args.len() != 4 {
        panic!("Usage: oxide_bbaexport family constids.inc out.bba");
    }

    let family = &args[1];
    let mut ids = IdStringDB::from_constids(&args[2])?;
    let outfile = File::create(&args[3])?;


    if family != "LIFCL" {
        // TODO: multiple family and device support
        panic!("unsupported family {}", &family);
    }

    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let mut db = Database::new(db_path_str);


    let tts = TileTypes::new(&mut db, &mut ids, "LIFCL", "LIFCL-40");
    let empty_chip = Chip::from_name(&mut db, "LIFCL-40");
    let mut lgrid = LocationGrid::new(&empty_chip, &mut db, &tts);
    lgrid.stamp_neighbours();
    let mut lts = LocationTypes::from_locs(&mut lgrid);
    lts.import_wires(&mut ids, &tts);

    let mut bba_str = BufWriter::new(outfile);
    let mut bba = BBAWriter::new(&mut bba_str);
    bba.pre("#include \"nextpnr.h\"")?;
    bba.pre("#include \"embed.h\"")?;
    bba.pre("NEXTPNR_NAMESPACE_BEGIN")?;
    bba.post(&format!("EmbeddedFile chipdb_file_{0}(\"nexus/chipdb-{0}.bin\", chipdb_blob_{0});", &family))?;
    bba.post("NEXTPNR_NAMESPACE_END")?;
    bba.push(&format!("chipdb_blob_{}", &family))?;
    bba.ref_label("db")?;

    let mut bba_s = BBAStructs::new(&mut bba);
    lts.write_locs_bba(&mut bba_s, &mut ids, &tts)?;
    lgrid.write_grid_bba(&mut bba_s, 0, &mut ids, &empty_chip)?;
    lgrid.write_chip_iodb(&mut bba_s, 0, &mut ids)?;
    bba_s.list_begin("chips")?;
    lgrid.write_chip_bba(&mut bba_s, 0, &empty_chip)?;
    ids.write_bba(&mut bba_s)?;
    bba_s.list_begin("db")?;
    bba_s.database(1, "LIFCL", "chips", lts.types.len(), "chip_tts")?;

    bba_s.out.pop()?;

    Ok(())
}
