use crate::bba::tiletype::*;
use crate::chip::*;
use crate::database::*;
use itertools::Itertools;
use std::collections::BTreeSet;

struct TileLocation {
    tiletypes: Vec<String>,
    neighbours: BTreeSet<Neighbour>,
}

impl TileLocation {
    pub fn setup(ch: &Chip, x: u32, y: u32, tts: &TileTypes) -> TileLocation {
        let tiles = ch.tiles_by_xy(x, y);
        let tiletypes: Vec<String> = tiles
            .iter()
            .map(|t| t.tiletype.to_string())
            .filter(|tt| tts.get(tt).unwrap().has_routing())
            .collect();
        let neighbours = tiletypes
            .iter()
            .map(|tt| tts.get(tt).unwrap().neighbours.iter())
            .flatten()
            .map(|x| x.clone())
            .collect();
        TileLocation {
            tiletypes: tiletypes,
            neighbours: neighbours,
        }
    }
}

struct LocationGrid {
    width: usize,
    height: usize,
    tiles: Vec<TileLocation>,
}

impl LocationGrid {
    pub fn new(ch: &Chip, tts: &TileTypes) -> LocationGrid {
        let width = ch.data.max_col + 1;
        let height = ch.data.max_row + 1;
        let locs = (0..height)
            .cartesian_product(0..width)
            .map(|(y, x)| TileLocation::setup(ch, x as u32, y as u32, tts))
            .collect();
        LocationGrid {
            width: width as usize,
            height: height as usize,
            tiles: locs,
        }
    }
    pub fn get(&self, x: usize, y: usize) -> Option<&TileLocation> {
        if x < self.width && y < self.height {
            Some(&self.tiles[y * self.width + x])
        } else {
            None
        }
    }
    pub fn get_mut(&mut self, x: usize, y: usize) -> Option<&mut TileLocation> {
        if x < self.width && y < self.height {
            Some(&mut self.tiles[y * self.width + x])
        } else {
            None
        }
    }
    // Make the neighbour array symmetric
    pub fn stamp_neighbours(&mut self) {
        for y in 0..self.height {
            for x in 0..self.width {
                let neighbours: Vec<Neighbour> = self
                    .get(x, y)
                    .unwrap()
                    .neighbours
                    .iter()
                    .map(|x| x.clone())
                    .collect();
                for n in neighbours {
                    match n {
                        Neighbour::RelXY { rel_x, rel_y } => {
                            let nx = (x as i32) + rel_x;
                            let ny = (y as i32) + rel_y;
                            if nx >= 0
                                && ny >= 0
                                && (nx as usize) < self.width
                                && (ny as usize) < self.height
                            {
                                let other = self.get_mut(nx as usize, ny as usize).unwrap();
                                other.neighbours.insert(Neighbour::RelXY {
                                    rel_x: -rel_x,
                                    rel_y: -rel_y,
                                });
                            }
                        }
                        _ => {
                            // FIXME: globals
                        }
                    }
                }
            }
        }
    }
}

struct LocationType {}
