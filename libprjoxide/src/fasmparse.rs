use std::collections::BTreeMap;
use std::convert::TryInto;
use std::fs::File;
use std::io::*;

use rug::Integer;

/*
Parser for the subset of FASM that Oxide cares about

Note that this does some preprocessing on features to speed up
downstream usage.

The first part of a feature, split by '.' is considered the tile
if 'PIP' follows it is a pip of form to_wire.from_wire
if it is vector style it is a word
otherwise it is an enum

*/

pub struct FasmTile {
    pub pips: BTreeMap<String, String>,
    pub enums: BTreeMap<String, String>,
    pub words: BTreeMap<String, Integer>,
}

impl FasmTile {
    pub fn new() -> FasmTile {
        FasmTile {
            pips: BTreeMap::new(),
            enums: BTreeMap::new(),
            words: BTreeMap::new(),
        }
    }
}

pub struct ParsedFasm {
    pub attrs: Vec<(String, String)>,
    pub tiles: BTreeMap<String, FasmTile>,
}

impl ParsedFasm {
    pub fn parse(filename: &str) -> Result<ParsedFasm> {
        let mut p = ParsedFasm {
            attrs: Vec::new(),
            tiles: BTreeMap::new(),
        };
        let file = File::open(filename)?;
        let reader = BufReader::new(file);
        for (lineno, line) in reader.lines().enumerate() {
            let l: String = line?;
            let first_nonblank = l.find(|c: char| !c.is_whitespace());
            if first_nonblank == None {
                continue;
            }
            let first_nonblank = first_nonblank.unwrap();
            let comment_start = l.find(|c: char| c == '#').unwrap_or(l.len());
            if first_nonblank >= comment_start {
                continue;
            }
            let mut buf = &l[first_nonblank..comment_start];

            let get_ident = |parsebuf: &mut &str| -> String {
                let end_index = parsebuf
                    .find(|c: char| !c.is_ascii_alphanumeric() && c != '_')
                    .unwrap_or(parsebuf.len());
                let token = &parsebuf[0..end_index];
                *parsebuf = &parsebuf[end_index..];
                token.to_string()
            };
            let get_attr_key = |parsebuf: &mut &str| -> String {
                let end_index = parsebuf
                    .find(|c: char| !c.is_ascii_alphanumeric() && c != '_' && c != '.')
                    .unwrap_or(parsebuf.len());
                let token = &parsebuf[0..end_index];
                *parsebuf = &parsebuf[end_index..];
                token.to_string()
            };
            let assert_token = |parsebuf: &mut &str, tok: &str| {
                if tok.len() > parsebuf.len() || &parsebuf[0..tok.len()] != tok {
                    panic!("expected token {} on line {}", tok, lineno + 1);
                }
                *parsebuf = &&parsebuf[tok.len()..];
            };
            let check_token = |parsebuf: &mut &str, tok: &str| -> bool {
                if tok.len() > parsebuf.len() || &parsebuf[0..tok.len()] != tok {
                    false
                } else {
                    *parsebuf = &parsebuf[tok.len()..];
                    true
                }
            };
            let skip_whitespace = |parsebuf: &mut &str| {
                let end_index = parsebuf
                    .find(|c: char| !c.is_whitespace())
                    .unwrap_or(parsebuf.len());
                *parsebuf = &parsebuf[end_index..];
            };
            let get_integer = |parsebuf: &mut &str| -> i32 {
                let end_index = parsebuf
                    .find(|c: char| !c.is_ascii_digit())
                    .unwrap_or(parsebuf.len());
                if end_index == 0 {
                    panic!("expected numeric value on line {}", lineno + 1);
                }
                let val = parsebuf[0..end_index].parse::<i32>().unwrap();
                *parsebuf = &parsebuf[end_index..];
                val
            };
            let get_char = |parsebuf: &mut &str| -> char {
                let ch = parsebuf.chars().next().unwrap();
                *parsebuf = &parsebuf[1..];
                ch
            };
            let get_value = |parsebuf: &mut &str| -> Integer {
                skip_whitespace(parsebuf);
                let width_or_value = get_integer(parsebuf);
                skip_whitespace(parsebuf);
                if !check_token(parsebuf, "'") {
                    return Integer::from(width_or_value);
                }
                skip_whitespace(parsebuf);
                let base = get_char(parsebuf);
                let digits = get_ident(parsebuf);
                Integer::from(
                    match base {
                        'b' => Integer::parse_radix(&digits, 2),
                        'o' => Integer::parse_radix(&digits, 8),
                        'd' => Integer::parse_radix(&digits, 10),
                        'h' => Integer::parse_radix(&digits, 16),
                        _ => panic!("unsupported base '{} on line {}", base, lineno + 1),
                    }
                    .unwrap(),
                )
            };
            let get_attr_value = |parsebuf: &mut &str| -> String {
                if check_token(parsebuf, "\"") {
                    // String
                    let end_index = parsebuf.find('"').unwrap();
                    let val = &parsebuf[0..end_index];
                    *parsebuf = &parsebuf[end_index + 1..];
                    val.to_string()
                } else {
                    // Not string
                    get_attr_key(parsebuf)
                }
            };
            if check_token(&mut buf, "{") {
                skip_whitespace(&mut buf);
                while !check_token(&mut buf, "}") {
                    let key = get_attr_key(&mut buf);
                    skip_whitespace(&mut buf);
                    assert_token(&mut buf, "=");
                    skip_whitespace(&mut buf);
                    p.attrs.push((key, get_attr_value(&mut buf)));
                    skip_whitespace(&mut buf);
                    if !check_token(&mut buf, ",") {
                        assert_token(&mut buf, "}");
                        break;
                    }
                }
            } else {
                let tilename = get_ident(&mut buf).replace("__", ":");
                let tile_data = p.tiles.entry(tilename).or_insert_with(FasmTile::new);
                assert_token(&mut buf, ".");
                if check_token(&mut buf, "PIP.") {
                    // It's a pip
                    let to_wire = get_ident(&mut buf).replace("__", ":");
                    assert_token(&mut buf, ".");
                    let from_wire = get_ident(&mut buf).replace("__", ":");
                    tile_data.pips.insert(to_wire, from_wire);
                } else {
                    let mut feature_split = Vec::new();
                    loop {
                        feature_split.push(get_ident(&mut buf));
                        if !check_token(&mut buf, ".") {
                            break;
                        }
                    }
                    skip_whitespace(&mut buf);
                    if check_token(&mut buf, "[") {
                        skip_whitespace(&mut buf);
                        // Word style setting
                        let key = feature_split.join(".");
                        let end_bit: u32 = get_integer(&mut buf).try_into().unwrap();
                        skip_whitespace(&mut buf);
                        let mut start_bit = end_bit;
                        skip_whitespace(&mut buf);
                        if check_token(&mut buf, ":") {
                            skip_whitespace(&mut buf);
                            start_bit = get_integer(&mut buf).try_into().unwrap();
                            skip_whitespace(&mut buf);
                        }
                        assert!(end_bit >= start_bit);
                        assert_token(&mut buf, "]");
                        skip_whitespace(&mut buf);
                        let value = if check_token(&mut buf, "=") {
                            skip_whitespace(&mut buf);
                            get_value(&mut buf)
                        } else {
                            Integer::from(1)
                        };
                        let dest = tile_data
                            .words
                            .entry(key)
                            .or_insert_with(|| Integer::from(0));
                        let count: u32 = (end_bit - start_bit) + 1;
                        for i in 0..count {
                            dest.set_bit(start_bit + i, value.get_bit(i));
                        }
                    } else {
                        // Enum style setting
                        let key = feature_split[0..feature_split.len() - 1].join(".");
                        let value = &feature_split[feature_split.len() - 1];
                        tile_data.enums.insert(key, value.to_string());
                    }
                }
            }
        }
        Ok(p)
    }

    pub fn dump(&self, out: &mut dyn Write) -> Result<()> {
        for (akey, aval) in self.attrs.iter() {
            writeln!(out, "{{ {}=\"{}\" }}", akey, aval)?;
        }
        for (tile, tdata) in self.tiles.iter() {
            for (to_wire, from_wire) in tdata.pips.iter() {
                writeln!(out, "{}.PIP.{}.{}", tile, to_wire, from_wire)?;
            }
            for (name, opt) in tdata.enums.iter() {
                writeln!(out, "{}.{}.{}", tile, name, opt)?;
            }
            for (name, val) in tdata.words.iter() {
                if val.significant_bits() > 0 {
                    writeln!(
                        out,
                        "{}.{}[{}:0] = {}'b{:b}",
                        tile,
                        name,
                        val.significant_bits() - 1,
                        val.significant_bits(),
                        val
                    )?;
                }
            }
            if !tdata.pips.is_empty() || !tdata.enums.is_empty() || !tdata.words.is_empty() {
                writeln!(out, "")?;
            }
        }
        Ok(())
    }
}
