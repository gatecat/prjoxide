use crate::database::*;
use std::cmp::{max, min};
use std::fs::File;
use std::io::Write;

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
