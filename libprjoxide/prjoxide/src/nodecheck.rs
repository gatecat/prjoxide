use crate::chip::*;
use crate::database::*;
use std::collections::BTreeSet;
use std::fs::File;
use std::io::*;

pub fn check(db: &mut Database, c: &Chip, nodefile: &str) {
    let f = File::open(nodefile).unwrap();
    let reader = BufReader::new(f);
    let mut lattice_pips = BTreeSet::<(String, String)>::new(); // (from, to)
    let mut oxide_pips = BTreeSet::<(String, String)>::new(); // (from, to)
    for line in reader.lines() {
        let l = line.unwrap();
        let s = l.split(' ').collect::<Vec<&str>>();
        if s.len() < 3 {
            continue;
        }
        if s[1] == "-->" {
            lattice_pips.insert((s[0].to_string(), s[2].to_string()));
        } else if s[1] == "<--" {
            lattice_pips.insert((s[2].to_string(), s[0].to_string()));
        }
    }

    for tile in c.tiles.iter() {
        let tdb = db.tile_bitdb(&c.family, &tile.tiletype);
        let norm_wire = |w: &str| {
            let sep_pos = w.find(':');
            if let Some(sp) = sep_pos {
                let prefix = &w[0..sp];
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
                        _ => {
                            return None; // Skip global wires etc
                        }
                    }
                }
                Some(format!(
                    "R{}C{}_{}",
                    tile.y as i32 + rel_y,
                    tile.x as i32 + rel_x,
                    &w[sp + 1..]
                ))
            } else {
                Some(format!("R{}C{}_{}", tile.y, tile.x, w))
            }
        };
        // Currently just checking fixed conns - could check pips too
        for (to_wire, conns) in tdb.db.conns.iter() {
            let norm_to_wire = norm_wire(to_wire);
            if let Some(tw) = norm_to_wire {
                for from_wire in conns.iter().filter_map(|c| norm_wire(&c.from_wire)) {
                    oxide_pips.insert((from_wire, tw.to_string()));
                }
            }
        }
    }
    for (from, to) in oxide_pips.iter() {
        if !lattice_pips.contains(&(from.to_string(), to.to_string())) {
            eprintln!("{} --> {}", from, to);
        }
    }
}
