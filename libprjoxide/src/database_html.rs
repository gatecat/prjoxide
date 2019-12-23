use crate::database::*;
use std::cmp::{max, min};
use std::collections::BTreeSet;
use std::fs::File;
use std::io::Write;
use std::iter::FromIterator;

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

pub fn write_bits_html(db: &mut Database, fam: &str, device: &str, tiletype: &str, filepath: &str) {
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
    let mut html = File::create(filepath).unwrap();
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

    // Write out the bit grid as HTML
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
            writeln!(html, "</td>").unwrap();
        }
        writeln!(html, "</table>").unwrap();
    }
    writeln!(html, "</body></html>").unwrap();
}
