use crate::sites::*;
use std::collections::BTreeSet;

pub const LUT4_PIN_MAP : &[(&str, &str)] = &[
    ("A", "A"),
    ("B", "B"),
    ("C", "C"),
    ("D", "D"),
    ("Z", "F"),
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
    ("OXIDE_COMB", &["LUT4"]),
    ("OXIDE_FF", &["FD1P3BX", "FD1P3DX", "FD1P3IX", "FD1P3JX"]),
    ("SEIO33_CORE", &["IB", "OB"]),
    ("SEIO18_CORE", &["IB", "OB"]),
];

fn conv_map(map: &[(&str, &str)]) -> Vec<(String, String)> {
    map.iter().map(|(c, b)| (c.to_string(), b.to_string())).collect()
}

fn get_map_for_cell_bel(cell_type: &str, _bel: &SiteBel) -> Vec<(String, String)> {
    match cell_type {
        "LUT4" => conv_map(LUT4_PIN_MAP),
        "FD1P3BX" => conv_map(FD1P3BX_PIN_MAP),
        "FD1P3DX" => conv_map(FD1P3DX_PIN_MAP),
        "FD1P3IX" => conv_map(FD1P3IX_PIN_MAP),
        "FD1P3JX" => conv_map(FD1P3JX_PIN_MAP),
        "IB" => conv_map(IB_PIN_MAP),
        "OB" => conv_map(OB_PIN_MAP),
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
                    pin_map: get_map_for_cell_bel(cell_type, site.bels.iter().find(|b| &b.bel_type == bel_type).unwrap()),
                });
            }
        }
    }
    return map;
}
