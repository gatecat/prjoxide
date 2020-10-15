use prjoxide::bitstream::*;
use prjoxide::database::*;

use std::fs::File;
use std::io::*;
use std::iter::FromIterator;

fn main() -> Result<()> {
    // FIXME: make this into a useful tool, not just a debugging utility
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());
    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let mut db = Database::new(db_path_str);
    let chip = BitstreamParser::parse_file(&mut db, &args[1]).unwrap();

    let mut outfile = File::create(&args[2])?;

    writeln!(outfile, "{{ oxide.device=\"{}\" }}", chip.device)?;
    writeln!(outfile, "{{ oxide.device_variant=\"{}\" }}", chip.variant)?;
    writeln!(outfile, "")?;

    for metadata in chip.metadata.iter() {
        writeln!(outfile, "{{ oxide.meta=\"{}\" }}", metadata)?;
    }
    if !chip.metadata.is_empty() {
        writeln!(outfile, "")?;
    }

    for tile in chip.tiles {
        tile.write_fasm(&mut db, &mut outfile);
    }

    for (addr, val) in chip.ipconfig.iter() {
        writeln!(outfile, "IP.0x{:08X}[7:0] = 8'h{:02X};", addr, val)?;
    }

    Ok(())
}
