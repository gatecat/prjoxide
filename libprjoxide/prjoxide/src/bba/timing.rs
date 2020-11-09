use crate::bba::bbastruct::*;
use crate::bba::idstring::*;
use crate::chip::*;

// Structures to represent imported timing data close to what we write out for nextpnr
pub struct BBAPropDelay {
	pub from_port: IdString,
	pub to_port: IdString,
	pub min_delay: i32,
	pub max_delay: i32,
}

pub struct BBASetupHold {
	pub sig_port: IdString,
	pub clock_port: IdString,
	pub min_setup: i32,
	pub max_setup: i32,
	pub min_hold: i32,
	pub max_hold: i32,
}

pub struct BBACellTiming {
	pub cell_type: IdString,
	pub cell_variant: IdString,
	pub prop_delays: Vec<BBAPropDelay>,
	pub setup_holds: Vec<BBASetupHold>,
}

pub struct BBAPipTiming {
	pub min_delay: i32,
	pub max_delay: i32,
	pub min_fanout_adder: i32,
	pub max_fanout_adder: i32,
}

pub struct BBASpeedGrade {
	pub name: String,
	pub cell_types: Vec<BBACellTiming>,
	pub pp_classes: Vec<BBAPipTiming>,
}
