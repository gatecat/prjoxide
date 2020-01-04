use crate::database::*;
use std::collections::{BTreeSet, HashMap};

#[derive(PartialEq, Eq, PartialOrd, Ord, Hash, Clone)]
pub enum BranchSide {
    Left,
    Right,
}

#[derive(PartialEq, Eq, PartialOrd, Ord, Hash, Clone)]
pub enum Neighbour {
    RelXY { rel_x: i32, rel_y: i32 },
    Branch,
    BranchDriver { side: BranchSide },
    Spine,
    HRow,
    Global,
    DQSGroup,
}

impl Neighbour {
    pub fn parse(s: &str) -> Option<Neighbour> {
        let sep_pos = s.find(':')?;
        let prefix = &s[0..sep_pos];
        Some(match prefix {
            "BRANCH" => Neighbour::Branch,
            "BRANCH_L" => Neighbour::BranchDriver {
                side: BranchSide::Left,
            },
            "BRANCH_R" => Neighbour::BranchDriver {
                side: BranchSide::Right,
            },
            "SPINE" => Neighbour::Spine,
            "HROW" => Neighbour::HRow,
            "G" => Neighbour::Global,
            "DQSG" => Neighbour::DQSGroup,
            _ => {
                let mut rel_x = 0;
                let mut rel_y = 0;
                let mut tokens = Vec::new();
                let mut last = 0;
                for (index, _) in
                    prefix.match_indices(|c| c == 'N' || c == 'E' || c == 'S' || c == 'W')
                {
                    if last != index {
                        tokens.push(&prefix[last..index]);
                    }
                    last = index;
                }
                tokens.push(&prefix[last..]);
                for tok in tokens {
                    match tok.chars().nth(0).unwrap() {
                        'N' => rel_y = -tok[1..].parse::<i32>().unwrap(),
                        'S' => rel_y = tok[1..].parse::<i32>().unwrap(),
                        'E' => rel_x = tok[1..].parse::<i32>().unwrap(),
                        'W' => rel_x = -tok[1..].parse::<i32>().unwrap(),
                        _ => panic!("bad pos token {}", tok),
                    }
                }
                Neighbour::RelXY { rel_x, rel_y }
            }
        })
    }
}

pub struct TileType {
    data: TileBitsDatabase,
    pub neighbours: BTreeSet<Neighbour>,
}

impl TileType {
    pub fn new(db: &mut Database, fam: &str, tt: &str) -> TileType {
        let mut tt = TileType {
            data: db.tile_bitdb(fam, tt).db.clone(),
            neighbours: BTreeSet::new(),
        };
        tt.neighbours = tt
            .get_wires()
            .iter()
            .filter_map(|w| Neighbour::parse(w))
            .collect();
        return tt;
    }

    pub fn has_routing(&self) -> bool {
        !self.data.pips.is_empty() || !self.data.conns.is_empty()
    }

    pub fn get_wires(&self) -> BTreeSet<String> {
        let mut wires = BTreeSet::new();
        for (to_wire, wire_pips) in self.data.pips.iter() {
            wires.insert(to_wire.to_string());
            for from_wire in wire_pips.iter().map(|x| &x.from_wire) {
                wires.insert(from_wire.to_string());
            }
        }
        for (to_wire, wire_conns) in self.data.conns.iter() {
            wires.insert(to_wire.to_string());
            for from_wire in wire_conns.iter().map(|x| &x.from_wire) {
                wires.insert(from_wire.to_string());
            }
        }
        return wires;
    }
}

pub struct TileTypes {
    types: HashMap<String, TileType>,
}

impl TileTypes {
    pub fn new(db: &mut Database, fam: &str, dev: &str) -> TileTypes {
        let tg = db.device_tilegrid(fam, dev);
        let unique_tiletypes: BTreeSet<String> =
            tg.tiles.iter().map(|t| t.1.tiletype.to_string()).collect();
        let mut types: HashMap<String, TileType> = HashMap::new();
        for tt in unique_tiletypes.iter() {
            types.insert(tt.to_string(), TileType::new(db, fam, tt));
        }
        TileTypes { types }
    }
    pub fn get(&self, tt: &str) -> Option<&TileType> {
        self.types.get(tt)
    }
}
