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
    pub fn run(&self) {

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
    pub fn run(&self) {
        
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
    pub fn run(&self) {
        
    }
}

fn main() {
    let opts: Opts = Opts::parse();
    match opts.subcmd {
        SubCommand::Pack(t) => {
            t.run();
        }
        SubCommand::Unpack(t) => {
            t.run();
        }
        SubCommand::BBAExport(t) => {
            t.run();
        }
    }

}
