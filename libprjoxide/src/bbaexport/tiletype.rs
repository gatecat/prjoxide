use crate::database::*;

struct TileType<'a> {
	data: &'a TileBitsData,
	neighbours: Vec<(i32, i32)>
}

impl<'a> TileType<'a> {
	pub fn new(db: &'a mut Database, fam: &str, tt: &str) -> TileType<'a> {
		TileType {
			data: db.tile_bitdb(fam, tt)
		}
	}

	pub fn find_neighbours() {

	}
}
