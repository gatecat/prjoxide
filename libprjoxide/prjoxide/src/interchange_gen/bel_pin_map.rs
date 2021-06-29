use crate::sites::*;
use std::collections::BTreeSet;

pub const LUT4_PIN_MAP : &[(&str, &str)] = &[
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("Z", "F"),
];

pub const CARRY_LUT_PIN_MAP : &[(&str, &str)] = &[
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("S", "F"),
    ("CIN", "FCI"),
    ("COUT", "FCO"),
];

pub const DPRAM_LUT_PIN_MAP : &[(&str, &str)] = &[
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("Z", "F"),
    ("WAD0", "WAD0"),
    ("WAD1", "WAD1"),
    ("WAD2", "WAD2"),
    ("WAD3", "WAD3"),
    ("WDI", "WDI"),
    ("WCK", "WCK"),
    ("WRE", "WRE"),
];


// TODO: need to add an extra pip to use LUT->DI path
const FD1P3BX_PIN_MAP : &[(&str, &str)] = &[
    ("D", "M"),
    ("CK", "CLK"),
    ("SP", "CE"),
    ("PD", "LSR"),
    ("Q", "Q"),
];
const FD1P3DX_PIN_MAP : &[(&str, &str)] = &[
    ("D", "M"),
    ("CK", "CLK"),
    ("SP", "CE"),
    ("CD", "LSR"),
    ("Q", "Q"),
];
const FD1P3IX_PIN_MAP : &[(&str, &str)] = &[
    ("D", "M"),
    ("CK", "CLK"),
    ("SP", "CE"),
    ("CD", "LSR"),
    ("Q", "Q"),
];
const FD1P3JX_PIN_MAP : &[(&str, &str)] = &[
    ("D", "M"),
    ("CK", "CLK"),
    ("SP", "CE"),
    ("PD", "LSR"),
    ("Q", "Q"),
];

const IB_PIN_MAP : &[(&str, &str)] = &[
    ("I", "B"),
    ("O", "O"),
];

const OB_PIN_MAP : &[(&str, &str)] = &[
    ("I", "I"),
    ("O", "B"),
];

// TODO: add back DFFs once we have some constraints set up

const BEL_CELL_TYPES : &[(&str, &[&str])] = &[
    ("OXIDE_COMB", &["LUT4", "CARRY_LUT", "DPRAM_LUT"]),
    ("OXIDE_FF", &["FD1P3BX", "FD1P3DX", "FD1P3IX", "FD1P3JX"]),
    ("SEIO33_CORE", &["IB", "OB"]),
    ("SEIO18_CORE", &["IB", "OB"]),
    ("DCC", &["DCC"]),
    ("OSC_CORE", &["OSC_CORE"]),
    ("OXIDE_EBR", &["DP16K_MODE", "PDP16K_MODE", "PDPSC16K_MODE"]),
];

fn conv_map(map: &[(&str, &str)]) -> Vec<(String, String)> {
    map.iter().map(|(c, b)| (c.to_string(), b.to_string())).collect()
}

fn auto_map(site: &Site, bel: &SiteBel) -> Vec<(String, String)> {
    bel.pins.iter().map(|p| &site.bel_pins[*p]).map(|p| (p.pin_name.to_string(), p.pin_name.to_string())).collect()
}

fn offset_bus(pin: &str, prefix: &str, rep: &str, offset: i32) -> String {
    let idx = pin[prefix.len()..].parse::<i32>().unwrap();
    format!("{}{}", rep, idx + offset)
}

fn bram_map(cell_type: &str, site: &Site, bel: &SiteBel) -> Vec<(String, String)> {
    let mut result = Vec::new();
    // PDP16K is a 1:1 map
    for bel_pin in bel.pins.iter().map(|p| &site.bel_pins[*p].pin_name) {
        let mut cell_pin = bel_pin.into();
        match &bel_pin[..] {
            "ONEERR" => { cell_pin = "ONEBITERR".into() },
            "TWOERR" => { cell_pin = "TWOBITERR".into() },
            _ => {},
        }
        match cell_type {
            "DP16K_MODE" => { /* all pins pass through */ }
            "PDPSC16K_MODE" | "PDP16K_MODE" => {
                if bel_pin.starts_with("ADA") { cell_pin = bel_pin.replace("ADA", "ADW") }
                else if bel_pin.starts_with("ADB") { cell_pin = bel_pin.replace("ADB", "ADR") }
                else if bel_pin.starts_with("CSA") { cell_pin = bel_pin.replace("CSA", "CSW") }
                else if bel_pin.starts_with("CSB") { cell_pin = bel_pin.replace("CSB", "CSR") }
                else if bel_pin == "CLKA" { cell_pin = if cell_type == "PDPSC16K_MODE" { "CLK" } else { "CLKW" }.into() }
                else if bel_pin == "CLKB" { cell_pin = if cell_type == "PDPSC16K_MODE" { "CLK" } else { "CLKR" }.into() }
                else if bel_pin == "CEA" { cell_pin = "CEW".into() }
                else if bel_pin == "CEB" { cell_pin = "CER".into() }
                else if bel_pin == "RSTA" || bel_pin == "RSTB" { cell_pin = "RST".into() }
                else if bel_pin.starts_with("DIA") { cell_pin = bel_pin.replace("DIA", "DI") }
                else if bel_pin.starts_with("DIB") { cell_pin = offset_bus(bel_pin, "DIB", "DI", 18) }
                else if bel_pin.starts_with("DOA") { cell_pin = offset_bus(bel_pin, "DOA", "DO", 18) }
                else if bel_pin.starts_with("DOB") { cell_pin = bel_pin.replace("DOB", "DO") }
                else if bel_pin == "WEA" || bel_pin == "WEB" { cell_pin = "VCC".into(); }
            },
            _ => unimplemented!(),
        }
        result.push((cell_pin, bel_pin.to_string()))
    }
    result.extend(conv_map(&[
        ("VCC", "DWS0"),
        ("VCC", "DWS1"),
        ("VCC", "DWS2"),
        ("VCC", "DWS3"),
        ("VCC", "DWS4"),
    ]));
    result
}

fn get_map_for_cell_bel(cell_type: &str, site: &Site, bel: &SiteBel) -> Vec<(String, String)> {
    match cell_type {
        "LUT4" => conv_map(LUT4_PIN_MAP),
        "CARRY_LUT" => conv_map(CARRY_LUT_PIN_MAP),
        "DPRAM_LUT" => conv_map(DPRAM_LUT_PIN_MAP),
        "RAMW" => auto_map(site, bel),
        "FD1P3BX" => conv_map(FD1P3BX_PIN_MAP),
        "FD1P3DX" => conv_map(FD1P3DX_PIN_MAP),
        "FD1P3IX" => conv_map(FD1P3IX_PIN_MAP),
        "FD1P3JX" => conv_map(FD1P3JX_PIN_MAP),
        "IB" => conv_map(IB_PIN_MAP),
        "OB" => conv_map(OB_PIN_MAP),
        "DCC" => auto_map(site, bel),
        "OSC_CORE" => auto_map(site, bel),
        "PDPSC16K_MODE" | "PDP16K_MODE" | "DP16K_MODE" => bram_map(cell_type, site, bel),
        _ => unimplemented!(),
    }
}

#[derive(Clone)]
pub struct PinMap {
    pub cell_type: String,
    pub bels: Vec<String>,
    pub pin_map: Vec<(String, String)>,
}

pub fn get_pin_maps(site: &Site) -> Vec<PinMap> {
    let mut map = Vec::new();
    let unique_bel_types : BTreeSet<String>
        = site.bels.iter().filter_map(|b| if b.bel_class == SiteBelClass::BEL { Some(b.bel_type.to_string()) } else { None }).collect();
    for bel_type in unique_bel_types.iter() {
        if let Some((_, cell_types)) = BEL_CELL_TYPES.iter().find(|(bt, _)| bt == bel_type) {
            for cell_type in cell_types.iter() {
                map.push(PinMap {
                    cell_type: cell_type.to_string(),
                    bels: site.bels.iter().filter_map(|b| if &b.bel_type == bel_type { Some(b.name.to_string()) } else { None }).collect(),
                    pin_map: get_map_for_cell_bel(cell_type, site, site.bels.iter().find(|b| &b.bel_type == bel_type).unwrap()),
                });
            }
        }
    }
    return map;
}
