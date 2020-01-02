mod bbaexport {
	pub mod idstring;
	pub mod tileloc;
	pub mod tiletype;
	pub mod idxset;
}
mod database;
use crate::bbaexport::idstring::*;

fn main() {
	let mut ids = IdStringDB::new();
}
