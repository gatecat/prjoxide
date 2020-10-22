use clap::Clap;

use prjoxide::bba::bbafile::*;
use prjoxide::bba::bbastruct::*;
use prjoxide::bba::idstring::*;
use prjoxide::bba::tileloc::*;
use prjoxide::bba::tiletype::*;

use prjoxide::bitstream::*;
use prjoxide::chip::*;
use prjoxide::database::*;
use prjoxide::fasmparse::*;

use std::fs::File;
use std::io::*;

use include_dir::{include_dir, Dir};

const DATABASE_DIR: Dir = include_dir!("../../database");

#[derive(Clap)]
#[clap(version = "0.1", author = "David Shah <dave@ds0.me>")]
struct Opts {
    #[clap(subcommand)]
    subcmd: SubCommand,
}

#[derive(Clap)]
enum SubCommand {
    #[clap(about = "pack FASM into a bitstream")]
    Pack(Pack),
    #[clap(about = "unpack a bitstream into FASM")]
    Unpack(Unpack),
    #[clap(about = "export a BBA file for the nextpnr build")]
    BBAExport(BBAExport),
}

#[derive(Clap)]
struct Pack {
    #[clap(about = "input FASM file")]
    fasm: String,
    #[clap(about = "output bitstream")]
    bitstream: String,
}

impl Pack {
    pub fn run(&self) -> Result<()> {
        let mut db = Database::new_builtin(DATABASE_DIR);
        let parsed_fasm = ParsedFasm::parse(&self.fasm).unwrap();

        let chip = Chip::from_fasm(&mut db, &parsed_fasm, None);
        let bs = BitstreamParser::serialise_chip(&chip);
        let mut outfile = File::create(&self.bitstream).unwrap();
        outfile.write_all(&bs)?;
        Ok(())
    }
}

#[derive(Clap)]
struct Unpack {
    #[clap(about = "input bitstream")]
    bitstream: String,
    #[clap(about = "output FASM file")]
    fasm: String,
}

impl Unpack {
    pub fn run(&self) -> Result<()> {
        let mut db = Database::new_builtin(DATABASE_DIR);
        let chip = BitstreamParser::parse_file(&mut db, &self.bitstream).unwrap();

        let mut outfile = File::create(&self.fasm)?;

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
            writeln!(outfile, "IP_UNKNOWN.0x{:08X}[7:0] = 8'h{:02X};", addr, val)?;
        }

        Ok(())
    }
}

#[derive(Clap)]
struct BBAExport {
    #[clap(about = "device family name")]
    family: String,
    #[clap(about = "path to nextpnr constids.inc")]
    constids: String,
    #[clap(about = "path to output bba file")]
    bba: String,
}

impl BBAExport {
    pub fn run(&self) -> Result<()> {
        let mut ids = IdStringDB::from_constids(&self.constids)?;
        let outfile = File::create(&self.bba)?;


        if self.family != "LIFCL" {
            // TODO: multiple family and device support
            panic!("unsupported family {}", &self.family);
        }

        let mut db = Database::new_builtin(DATABASE_DIR);

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
        bba.post(&format!("EmbeddedFile chipdb_file_{0}(\"nexus/chipdb-{0}.bin\", chipdb_blob_{0});", &self.family))?;
        bba.post("NEXTPNR_NAMESPACE_END")?;
        bba.push(&format!("chipdb_blob_{}", &self.family))?;
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
}

fn main() -> Result<()> {
    let opts: Opts = Opts::parse();
    match opts.subcmd {
        SubCommand::Pack(t) => {
            t.run()
        }
        SubCommand::Unpack(t) => {
            t.run()
        }
        SubCommand::BBAExport(t) => {
            t.run()
        }
    }

}
