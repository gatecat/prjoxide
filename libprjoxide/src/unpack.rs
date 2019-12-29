mod bitstream;
mod chip;
mod database;

use std::fs::File;
use std::io::Result;
use std::iter::FromIterator;

fn main() -> Result<()> {
    // FIXME: make this into a useful tool, not just a debugging utility
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());
    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let mut db = database::Database::new(db_path_str);
    let chip = bitstream::BitstreamParser::parse_file(&mut db, &args[1]).unwrap();

    let mut outfile = File::create(&args[2])?;

    for tile in chip.tiles {
        tile.write_fasm(&mut db, &mut outfile);
    }

    Ok(())
}
