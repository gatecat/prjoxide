mod chip;
mod database;
mod fasmparse;

use std::io::*;
use std::iter::FromIterator;

fn main() -> Result<()> {
    // FIXME: make this into a useful tool, not just a debugging utility
    let exe_path = std::env::current_exe()?;
    let args = Vec::from_iter(std::env::args());
    let db_path = exe_path.parent().unwrap().join("../../../database");
    let db_path_str = db_path.to_str().unwrap();
    let db = database::Database::new(db_path_str);
    let parsed_fasm = fasmparse::ParsedFasm::parse(&args[1]).unwrap();

    let mut bw = BufWriter::new(std::io::stdout());
    parsed_fasm.dump(&mut bw)?;
    Ok(())
}
