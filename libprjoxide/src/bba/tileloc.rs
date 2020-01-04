use crate::bba::idxset::*;
use crate::bba::tiletype::*;
use crate::chip::*;
use crate::database::*;

struct TileLocation {
    tiletypes: Vec<String>,
    neigbours: Vec<Neighbour>,
}

impl TileLocation {
    pub fn setup(db: &mut Database, ch: &Chip, x: u32, y: u32) {
        let tiles = ch.tiles_by_xy(x, y);
    }
}
