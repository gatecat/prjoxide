use crate::bels::*;
use crate::database::*;
use crate::docs::{md_file_to_html, md_to_html};
use std::cmp::{max, min};
use std::collections::BTreeSet;
use std::fs::File;
use std::io::Write;
use std::iter::FromIterator;
use std::path::Path;

// Get the shade colour for a tile type
fn get_colour(ttype: &str) -> &'static str {
    if ttype.contains("TAP") {
        return "#DDDDDD";
    } else if ttype.starts_with("SYSIO") {
        return "#88FF88";
    } else if ttype.starts_with("CIB") {
        return "#FF8888";
    } else if ttype.starts_with("PLC") {
        return "#8888FF";
    } else if ttype.starts_with("DUMMY") {
        return "#FFFFFF";
    } else if ttype.starts_with("MIB_EBR") || ttype.starts_with("EBR_") || ttype.starts_with("LRAM")
    {
        return "#FF88FF";
    } else if ttype.contains("DSP") || ttype.contains("ALU") {
        return "#FFFF88";
    } else if ttype.contains("PLL")
        || ttype.contains("DPHY")
        || ttype.contains("CDR")
        || ttype.contains("PCIE")
        || ttype.contains("EFB")
        || ttype.contains("PMU")
        || ttype.contains("ADC")
    {
        return "#88FFFF";
    } else {
        return "#888888";
    }
}

pub fn write_tilegrid_html(db: &mut Database, fam: &str, device: &str, filepath: &str) {
    let device_info = db.device_by_name(device).unwrap().2;
    let tilegrid = db.device_tilegrid(fam, device);
    let mut tiles: Vec<Vec<Vec<(&str, &str, &'static str)>>> =
        vec![vec![vec![]; (device_info.max_col + 1) as usize]; (device_info.max_row + 1) as usize];
    for (tileid, tiledata) in tilegrid.tiles.iter() {
        let name = tileid.split(':').next().unwrap();
        let colour = get_colour(&tiledata.tiletype);
        tiles[tiledata.y as usize][tiledata.x as usize].push((name, &tiledata.tiletype, colour));
    }
    let mut html = File::create(filepath).unwrap();
    write!(
        html,
        "<html>\n\
<head><title>{d} Tiles</title></head>\n\
<body>\n\
<h1>{d} Tilegrid</h1>\n\
<table style='font-size: 8pt; border: 2px solid black; text-align: center'>\n\
",
        d = device
    )
    .unwrap();
    for trow in tiles.iter() {
        writeln!(html, "<tr>").unwrap();
        let row_max_height = trow.iter().map(Vec::len).fold(0, max);
        let row_height = max(75, 30 * row_max_height);
        for tloc in trow.iter() {
            writeln!(
                html,
                "<td style='border: 2px solid black; height: {}px'>",
                row_height
            )
            .unwrap();
            for (name, ttype, colour) in tloc.iter() {
                writeln!(html, "<div style='height: {h}%; background-color: {c}'><em>{n}</em><br/><strong><a href='../tilehtml/{t}.html' style='color: black'>{t}</a></strong></div>",
                    h=(100.0 / (tloc.len() as f32)), c=colour, n=name, t=ttype).unwrap();
            }
            writeln!(html, "</td>").unwrap();
        }
        writeln!(html, "</tr>").unwrap();
    }
}

// Get the colour given the first letter of  a wire label
fn wire_colour(c: char) -> &'static str {
    match c {
        'A' => "#88FFFF",
        'B' => "#FF88FF",
        'C' => "#8888FF",
        'D' => "#FFFF88",
        'M' => "#FFBBBB",
        'H' => "#BBBBFF",
        'V' => "#FFFFBB",
        _ => "#FF8888",
    }
}

pub fn write_bits_html(
    db: &mut Database,
    docs_root: &str,
    fam: &str,
    device: &str,
    tiletype: &str,
    outdir: &str,
) {
    let tilegrid = db.device_tilegrid(fam, device);
    let mut nframes = 0;
    let mut nbits = 0;
    for tile in tilegrid.tiles.values() {
        if tile.tiletype == tiletype {
            nframes = tile.frames;
            nbits = tile.bits;
            break;
        }
    }

    let bitdb = &db.tile_bitdb(fam, tiletype).db;

    // Find the purpose of each bit
    // (frame, bit) --> (link, labels)
    let mut bitgrid: Vec<Vec<(BTreeSet<String>, Option<String>)>> =
        vec![vec![(BTreeSet::new(), None); nbits]; nframes];
    for (wordname, data) in bitdb.words.iter() {
        for (i, bits) in data.bits.iter().enumerate() {
            for bit in bits {
                bitgrid[bit.frame][bit.bit]
                    .0
                    .insert(format!("{}[{}]", wordname, i));
                bitgrid[bit.frame][bit.bit].1 = Some(format!("word_{}", wordname));
            }
        }
    }
    for (enumname, data) in bitdb.enums.iter() {
        for bit in data.options.values().flatten() {
            bitgrid[bit.frame][bit.bit]
                .0
                .insert(format!("{}", enumname));
            bitgrid[bit.frame][bit.bit].1 = Some(format!("enum_{}", enumname));
        }
    }
    for (sink, data) in bitdb.pips.iter() {
        for bit in data.iter().map(|x| x.bits.iter()).flatten() {
            bitgrid[bit.frame][bit.bit].0.insert(format!("{}", sink));
            bitgrid[bit.frame][bit.bit].1 = Some(format!("mux_{}", sink));
        }
    }

    // Write out prelude HTML
    let mut html = File::create(
        Path::new(outdir)
            .join("tilehtml")
            .join(format!("{}.html", tiletype))
            .to_str()
            .unwrap(),
    )
    .unwrap();
    write!(
        html,
        "<html> \n\
            <head><title>{} Bit Data</title>\n\
        ",
        tiletype
    )
    .unwrap();
    write!(
        html,
        "<script type=\"text/javascript\">\n\
            origClr = {{}};\n\
            origClass = \"\";\n\
            \n\
            function mov(event) {{\n\
                if (event.target.className != \"unknown\") {{\n\
                    origClass = event.target.className;\n\
                    var elems = document.getElementsByClassName(origClass);\n\
                    for(var i = 0; i < elems.length; i++) {{\n\
                       if(!(elems[i].id in origClr)) {{\n\
                          origClr[elems[i].id] = elems[i].style.backgroundColor;\n\
                       }}\n\
                       elems[i].style.backgroundColor = \"white\";\n\
                    }}\n\
\n\
                }}\n\
            }}\n\
            \n\
            function mou(event) {{\n\
                var elems = document.getElementsByClassName(origClass);\n\
                for(var i = 0; i < elems.length; i++) {{\n\
                   elems[i].style.backgroundColor = origClr[elems[i].id] || \"#ffffff\";\n\
                }}\n\
            }}\n\
            </script>\n\
            </head>\n\
            <body>\n\
            "
    )
    .unwrap();

    writeln!(html, "<h1>{} Tile Documentation</h1>", tiletype).unwrap();
    let tiledesc_path = Path::new(docs_root)
        .join("tiles")
        .join(format!("{}.md", tiletype));
    if tiledesc_path.exists() {
        writeln!(html, "{}", md_file_to_html(tiledesc_path.to_str().unwrap())).unwrap();
    }

    // f, b -> (group, label, colour)
    let get_bit_info = |frame: usize, bit: usize| -> (String, String, &'static str) {
        match &bitgrid[frame][bit].1 {
            Some(group) => {
                let mut label = '?';
                let mut colour = "#FFFFFF";
                if group.starts_with("mux") {
                    let us_pos = group.rfind('_').unwrap();
                    label = group.chars().nth(us_pos + 1).unwrap();
                    if label == 'J' {
                        label = group.chars().nth(us_pos + 2).unwrap();
                    }
                    colour = wire_colour(label);
                } else if group.starts_with("enum") || group.starts_with("word") {
                    let us_pos = group.rfind(|c| c == '_' || c == '.').unwrap();
                    label = group.chars().nth(us_pos + 1).unwrap();
                    colour = "#88FF88";
                }
                (group.to_string(), label.to_string(), colour)
            }
            None => ("unknown".to_string(), "&nbsp;".to_string(), "#FFFFFF"),
        }
    };

    // Write out links to bels
    let bels = get_tile_bels(tiletype);
    if !bels.is_empty() {
        writeln!(html, "<h2>Tile Bels</h2>").unwrap();
        writeln!(
            html,
            "<table class=\"bpins\" style=\"border-spacing:0\"><tr><th>Name</th><th>Type</th></tr>"
        )
        .unwrap();
        for (i, bel) in bels.iter().enumerate() {
            let style = match i % 2 {
                0 => " bgcolor=\"#dddddd\"",
                _ => "",
            };
            let belhtml_path = Path::new(outdir)
                .join("belhtml")
                .join(format!("{}_{}.html", tiletype, bel.name));
            write_bel_html(docs_root, tiletype, bel, belhtml_path.to_str().unwrap());
            writeln!(
                html,
                "<tr {s}><td style=\"padding-left: 20px; padding-right: 20px\"><a href='../belhtml/{tt}_{bn}.html'>{bn}</a></td>\n\
                <td style=\"padding-left: 20px; padding-right: 20px\">{bt}</td></tr>",
                s = style,
                bn = bel.name,
                bt = bel.beltype,
                tt = tiletype
            )
            .unwrap();
        }
        writeln!(html, "</table>").unwrap();
    }

    // Write out the bit grid as HTML
    writeln!(html, "<h2>Config Bitmap</h2>").unwrap();
    writeln!(
        html,
        "<table style='font-size: 8pt; border: 2px solid black; text-align: center'>"
    )
    .unwrap();
    for bit in 0..nbits {
        writeln!(html, "<tr style='height: 20px'>").unwrap();
        for frame in 0..nframes {
            let (group, label, colour) = get_bit_info(frame, bit);
            writeln!(html, "<td style='height: 100%; border: 2px solid black;'>").unwrap();
            let mut title = format!("F{}B{}", frame, bit);
            for funclabel in bitgrid[frame][bit].0.iter() {
                title.push('\n');
                title.push_str(funclabel);
            }
            writeln!(html, "<a href='#{g}' title='{t}' style='text-decoration: none; color: #000000'>\n\
                    <div id='f{f}b{b}' style='height: 100%; background-color: {c}; width: 12px' class='grp_{g}'\n\
                    onmouseover='mov(event);' onmouseout='mou(event);'>{l}</div></a></td>",
                    g=group, t=title, f=frame, b=bit, c=colour, l=label).unwrap();
        }
        writeln!(html, "</tr>").unwrap();
    }
    writeln!(html, "</table>").unwrap();
    // Write out muxes as html
    if !bitdb.pips.is_empty() {
        writeln!(html, "<h2>Routing Muxes</h2>").unwrap();
    }
    for (sink, data) in bitdb.pips.iter() {
        writeln!(
            html,
            "<h3 id=\"mux_{s}\">Mux driving <span class=\"mux_sink\">{s}</span></h3>",
            s = sink
        )
        .unwrap();
        writeln!(html, "<table class='mux'><tr><th>Source</th>").unwrap();
        let bitset: BTreeSet<(usize, usize)> = data
            .iter()
            .flat_map(|x| x.bits.iter())
            .map(|x| (x.frame, x.bit))
            .collect();
        for (frame, bit) in bitset.iter() {
            writeln!(
                html,
                "<th style='padding-left: 10px; padding-right: 10px'>F{}B{}</th>",
                frame, bit
            )
            .unwrap();
        }
        writeln!(html, "</tr>").unwrap();
        // Determine mux setting "truth table"
        let mut truthtable: Vec<(String, Vec<char>)> = data
            .iter()
            .map(|x| {
                (
                    x.from_wire.to_string(),
                    bitset
                        .iter()
                        .map(|&(f, b)| {
                            if x.bits.contains(&ConfigBit {
                                frame: f,
                                bit: b,
                                invert: false,
                            }) {
                                '1'
                            } else if x.bits.contains(&ConfigBit {
                                frame: f,
                                bit: b,
                                invert: true,
                            }) {
                                '0'
                            } else {
                                '-'
                            }
                        })
                        .collect(),
                )
            })
            .collect();

        let truth_key = |x: &[char]| -> String {
            String::from_iter(x.iter().map(|&c| match c {
                '-' => '0',
                o => o,
            }))
        };

        truthtable
            .sort_by(|(_n1, b1), (_n2, b2)| truth_key(b1).partial_cmp(&truth_key(b2)).unwrap());

        for (i, (from_wire, ttrow)) in truthtable.iter().enumerate() {
            let style = match i % 2 {
                0 => " bgcolor=\"#dddddd\"",
                _ => "",
            };
            writeln!(html, "<tr {s}><td>{f}</td>", s = style, f = from_wire).unwrap();
            for bit in ttrow.iter() {
                writeln!(html, "<td style=\"text-align: center\">{}</td>", bit).unwrap();
            }
            writeln!(html, "</tr>").unwrap();
        }
        writeln!(html, "</table>").unwrap();
    }

    // Write out words as HTML
    if !bitdb.words.is_empty() {
        writeln!(html, "<h2>Configuration Words</h2>").unwrap();
    }
    for (word, data) in bitdb.words.iter() {
        writeln!(
            html,
            "<h3 id='word_{w}'>Configuration word {w}</h3>",
            w = word
        )
        .unwrap();
        if !data.desc.is_empty() {
            let desc_html = md_to_html(&data.desc);
            writeln!(html, "{}", &desc_html).unwrap();
        }
        writeln!(html, "<table class='setword'>").unwrap();
        for (i, bits) in data.bits.iter().enumerate() {
            let style = match i % 2 {
                0 => " bgcolor=\"#dddddd\"",
                _ => "",
            };
            let cbits: Vec<String> = bits
                .iter()
                .map(|b| {
                    format!(
                        "{}F{}B{}",
                        match b.invert {
                            true => "!",
                            false => "",
                        },
                        b.frame,
                        b.bit
                    )
                })
                .collect();
            writeln!(html, "<tr {s}><td style=\"padding-left: 10px; padding-right: 10px\">{n}[{i}]</td><td style=\"padding-left: 10px; padding-right: 10px\">{b}</td></tr>"
                , s=style, n=word, i=i, b=cbits.join(" ")).unwrap();
        }
        writeln!(html, "</table>").unwrap();
    }

    // Write out enums as HTML
    if !bitdb.enums.is_empty() {
        writeln!(html, "<h2>Configuration Enums</h2>").unwrap();
    }
    for (en, data) in bitdb.enums.iter() {
        writeln!(
            html,
            "<h3 id='enum_{e}'>Configuration enum {e}</h3>",
            e = en
        )
        .unwrap();
        if !data.desc.is_empty() {
            let desc_html = md_to_html(&data.desc);
            writeln!(html, "{}", &desc_html).unwrap();
        }
        writeln!(html, "<table class='setenum'><tr><th>Value</th>").unwrap();
        let bitset: BTreeSet<(usize, usize)> = data
            .options
            .values()
            .flat_map(|x| x.iter())
            .map(|x| (x.frame, x.bit))
            .collect();
        for (frame, bit) in bitset.iter() {
            writeln!(
                html,
                "<th style='padding-left: 10px; padding-right: 10px'>F{}B{}</th>",
                frame, bit
            )
            .unwrap();
        }
        writeln!(html, "</tr>").unwrap();
        // Determine enum option "truth table"
        let truthtable: Vec<(String, Vec<char>)> = data
            .options
            .iter()
            .map(|(opt, bits)| {
                (
                    opt.to_string(),
                    bitset
                        .iter()
                        .map(|&(f, b)| {
                            if bits.contains(&ConfigBit {
                                frame: f,
                                bit: b,
                                invert: false,
                            }) {
                                '1'
                            } else if bits.contains(&ConfigBit {
                                frame: f,
                                bit: b,
                                invert: true,
                            }) {
                                '0'
                            } else {
                                '-'
                            }
                        })
                        .collect(),
                )
            })
            .collect();
        for (i, (opt, ttrow)) in truthtable.iter().enumerate() {
            let style = match i % 2 {
                0 => " bgcolor=\"#dddddd\"",
                _ => "",
            };
            writeln!(html, "<tr {s}><td>{f}</td>", s = style, f = opt).unwrap();
            for bit in ttrow.iter() {
                writeln!(html, "<td style=\"text-align: center\">{}</td>", bit).unwrap();
            }
            writeln!(html, "</tr>").unwrap();
        }
        writeln!(html, "</table>").unwrap();
    }

    let mut i = 0;

    if bitdb.conns.len() > 0 {
        writeln!(html, "<h3>Fixed Connections</h3>").unwrap();
        writeln!(html, "<table class=\"fconn\" style=\"border-spacing:0\"><tr><th>Source</th><th></th><th>Sink</th></tr>").unwrap();
        for (to_wire, conns) in bitdb.conns.iter() {
            for conn in conns.iter() {
                let style = match i % 2 {
                    0 => " bgcolor=\"#dddddd\"",
                    _ => "",
                };
                i += 1;
                writeln!(html, "<tr {s}><td style=\"padding-left: 10px; padding-right: 10px; margin-left: 0px;\">{f}</td><td>&rarr;</td>\n\
                <td style=\"padding-left: 10px; padding-right: 10px\">{t}</td></tr>", s=style, t=to_wire, f=conn.from_wire).unwrap();
            }
        }
        writeln!(html, "</table>").unwrap();
    }

    writeln!(html, "</body></html>").unwrap();
}

pub fn write_bel_html(docs_root: &str, tiletype: &str, bel: &Bel, filepath: &str) {
    // Write out prelude HTML
    let mut html = File::create(filepath).unwrap();
    writeln!(
        html,
        "<html> \n\
            <head>\n\
            <title>{tt}/{bn} ({bt}) Bel Documentation</title>\n\
            </head>\n\
            <body>\n\
            <h1>{tt}/{bn} ({bt}) Bel Documentation</h1>\n\
        ",
        tt = tiletype,
        bn = bel.name,
        bt = bel.beltype
    )
    .unwrap();
    for docname in &[
        &bel.beltype,
        &bel.name,
        &format!("{}_{}", &tiletype, &bel.name),
    ] {
        let tiledesc_path = Path::new(docs_root)
            .join("bels")
            .join(format!("{}.md", docname));
        if tiledesc_path.exists() {
            writeln!(html, "{}", md_file_to_html(tiledesc_path.to_str().unwrap())).unwrap();
        }
    }
    writeln!(html, "<h2>Bel Pins</h2>").unwrap();
    writeln!(html, "<table class=\"bpins\" style=\"border-spacing:0\"><tr><th>Pin</th><th></th><th>Wire</th><th></th></tr>").unwrap();
    for (i, pin) in bel.pins.iter().enumerate() {
        let style = match i % 2 {
            0 => " bgcolor=\"#dddddd\"",
            _ => "",
        };
        let arrow = match &pin.dir {
            PinDir::INPUT => "&larr;",
            PinDir::OUTPUT => "&rarr;",
            PinDir::INOUT => "&LeftRightArrow;",
        };
        writeln!(html, "<tr {s}><td style=\"padding-left: 20px; padding-right: 20px; margin-left: 0px;\">{p}</td><td>{a}</td>\n\
                <td style=\"padding-left: 20px; padding-right: 20px\">{w}</td><td>{d}</tr>", s=style, p=pin.name, a=arrow, w=&pin.wire.rel_name(), d=pin.desc).unwrap();
    }
    writeln!(html, "</table>").unwrap();
    writeln!(html, "</body></html>").unwrap();
}
