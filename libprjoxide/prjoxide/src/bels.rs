use std::collections::BTreeSet;
use crate::chip::*;
use crate::database::TileBitsDatabase;
use std::convert::TryInto;

// A reference to a wire in a relatively located tile
#[derive(Clone)]
pub struct RelWire {
    pub rel_x: i32,   // (bel.x + rel_x == tile.x)
    pub rel_y: i32,   // (bel.y + rel_y == tile.y)
    pub name: String, // wire name in tile
}

impl RelWire {
    pub fn prefix(total_rel_x : i32, total_rel_y : i32) -> String {
        let mut prefix = String::new();
        if total_rel_y < 0 {
            prefix.push_str(&format!("N{}", -total_rel_y));
        }
        if total_rel_y > 0 {
            prefix.push_str(&format!("S{}", total_rel_y));
        }
        if total_rel_x < 0 {
            prefix.push_str(&format!("W{}", -total_rel_x));
        }
        if total_rel_x > 0 {
            prefix.push_str(&format!("E{}", total_rel_x));
        }
        if !prefix.is_empty() {
            prefix.push(':');
        }
        prefix
    }
    pub fn rel_name(&self, bel_rel_x : i32, bel_rel_y : i32) -> String {
        let mut name = String::new();
        let total_rel_x = bel_rel_x + self.rel_x;
        let total_rel_y = bel_rel_y + self.rel_y;
        name.push_str(&RelWire::prefix(total_rel_x, total_rel_y));
        name.push_str(&self.name);
        name
    }
}

#[derive(Eq, PartialEq, Clone)]
pub enum PinDir {
    INPUT = 0,
    OUTPUT = 1,
    INOUT = 2,
}

#[derive(Clone)]
pub struct BelPin {
    pub name: String,  // name of pin on bel
    pub desc: String,  // description for documentation
    pub dir: PinDir,   // direction
    pub wire: RelWire, // reference to wire in tile
}

impl BelPin {
    pub fn new(
        name: &str,
        desc: &str,
        dir: PinDir,
        wirename: &str,
        rel_x: i32,
        rel_y: i32,
    ) -> BelPin {
        BelPin {
            name: name.to_string(),
            desc: desc.to_string(),
            dir: dir,
            wire: RelWire {
                rel_x: rel_x,
                rel_y: rel_y,
                name: wirename.to_string(),
            },
        }
    }

    // Standard postfixed wirename scheme
    pub fn new_p(
        name: &str,
        desc: &str,
        dir: PinDir,
        postfix: &str,
        rel_x: i32,
        rel_y: i32,
    ) -> BelPin {
        BelPin {
            name: name.to_string(),
            desc: desc.to_string(),
            dir: dir,
            wire: RelWire {
                rel_x: rel_x,
                rel_y: rel_y,
                name: format!("J{}_{}", name, postfix),
            },
        }
    }
    // Logical->physical mapped postfixed wirename scheme
    pub fn new_mapped(
        name: &str,
        desc: &str,
        dir: PinDir,
        physpin: &str,
        postfix: &str,
        rel_x: i32,
        rel_y: i32,
    ) -> BelPin {
        BelPin {
            name: name.to_string(),
            desc: desc.to_string(),
            dir: dir,
            wire: RelWire {
                rel_x: rel_x,
                rel_y: rel_y,
                name: format!("J{}_{}", physpin, postfix),
            },
        }
    }
}

pub struct Bel {
    pub name: String,
    pub beltype: String,
    pub pins: Vec<BelPin>,
    pub rel_x: i32,
    pub rel_y: i32,
    pub z: u32,
}

// Macros for common cases
macro_rules! input {
	($($rest:expr),*) =>
		( def_pin!(PinDir::INPUT, $($rest),*) );
}

macro_rules! output {
	($($rest:expr),*) =>
		( def_pin!(PinDir::OUTPUT, $($rest),*) );
}

macro_rules! def_pin {
    ($dir: expr, $postfix: expr, $name: expr) => {
        BelPin::new_p($name, "", $dir, $postfix, 0, 0)
    };

    ($dir: expr,$postfix: expr, $name: expr, $desc: expr) => {
        BelPin::new_p($name, $desc, $dir, $postfix, 0, 0)
    };
    ($dir: expr,$postfix: expr, $name: expr, $desc: expr, $rel_x: expr, $rel_y: expr) => {
        BelPin::new_p($name, $desc, $dir, $postfix, $rel_x, $rel_y)
    };
}

macro_rules! input_m {
    ($($rest:expr),*) =>
        ( def_pin_mapped!(PinDir::INPUT, $($rest),*) );
}

macro_rules! output_m {
    ($($rest:expr),*) =>
        ( def_pin_mapped!(PinDir::OUTPUT, $($rest),*) );
}

macro_rules! inout_m {
    ($($rest:expr),*) =>
        ( def_pin_mapped!(PinDir::INOUT, $($rest),*) );
}

macro_rules! def_pin_mapped {
    ($dir: expr, $postfix: expr, $name: expr) => {
        BelPin::new_p($name, "", $dir, $physpin, $postfix, 0, 0)
    };

    ($dir: expr,$postfix: expr, $name: expr, $physpin: expr, $desc: expr) => {
        BelPin::new_mapped($name, $desc, $dir, $physpin, $postfix, 0, 0)
    };
}

const Z_TO_CHAR: [char; 4] = ['A', 'B', 'C', 'D'];

impl Bel {
    // Copy inputs and outputs based on connectivity in the routing graph
    fn get_io(db: &TileBitsDatabase, postfix: &str, rel_x : i32, rel_y : i32) -> Vec<BelPin> {
        let mut pins = Vec::new();
        let prefix = RelWire::prefix(rel_x, rel_y);

        let mut add_wire = |wire : &str, dir| {
            if wire.starts_with(&prefix) && wire.ends_with(postfix) {
                // Remove the relative location prefix
                let wire_name = &wire[prefix.len()..];
                // Determine the pin name by removing the postfix
                let mut pin_name = &wire_name[..wire_name.len()-postfix.len()];

                if pin_name.starts_with('J') {
                    // If applicable, generally for CIB signals, remove the mysterious 'J' prefix
                    pin_name = &pin_name[1..];
                }

                pins.push(BelPin::new(&pin_name, "", dir, wire_name, 0, 0));
            }
        };

        let mut sink_wires :BTreeSet<String> =  BTreeSet::new();
        let mut src_wires :BTreeSet<String> = BTreeSet::new();

        for (to_wire, pips) in db.pips.iter() {
            for pip in pips.iter() {
                // Look at pips that start with, or end with, the postfix
                // but not both as that would be a route-through
                if to_wire.ends_with(postfix) && !pip.from_wire.ends_with(postfix) {
                    sink_wires.insert(to_wire.to_string());
                }
                if !to_wire.ends_with(postfix) && pip.from_wire.ends_with(postfix) {
                    src_wires.insert(pip.from_wire.to_string());
                }
            }
        }

        for (to_wire, conns) in db.conns.iter() {
            for conn in conns.iter() {
                // Look at pips that start with, or end with, the postfix
                // but not both as that would be a route-through
                if to_wire.ends_with(postfix) && !conn.from_wire.ends_with(postfix) {
                    sink_wires.insert(to_wire.to_string());
                }
                if !to_wire.ends_with(postfix) && conn.from_wire.ends_with(postfix) {
                    src_wires.insert(conn.from_wire.to_string());
                }
            }
        }

        for src_wire in src_wires.iter() {
            add_wire(src_wire, PinDir::OUTPUT);
        }

        for sink_wire in sink_wires.iter() {
            add_wire(sink_wire, PinDir::INPUT);
        }
/*
        *** temporarily disabled check due to missing DSP wires
        if pins.is_empty() {
            panic!("no IO pins found for postfix {}, prefix {}", postfix, prefix);
        }
*/
        return pins;
    }

    pub fn make_oxide_ff(slice: usize, ff: usize) -> Bel {
        let ch = Z_TO_CHAR[slice];
        let postfix = format!("SLICE{}", ch);
        let pins = vec![
            input!(&postfix, "CLK", "FF clock"),
            input!(&postfix, "CE", "FF clock enable"),
            input!(&postfix, "LSR", "FF local set/reset"),
            input_m!(
                &postfix,
                "DI",
                &format!("DI{}", ff),
                "FF input from LUT/MUX output"
            ),
            input_m!(
                &postfix,
                "M",
                &format!("M{}", ff),
                "FF direct input from fabric M signal"
            ),
            output_m!(&postfix, "Q", &format!("Q{}", ff), "FF output"),
        ];
        Bel {
            name: format!("{}_FF{}", &postfix, ff),
            beltype: String::from("OXIDE_FF"),
            pins: pins,
            rel_x: 0,
            rel_y: 0,
            z: (slice << 3 | (ff + 2)) as u32,
        }
    }

    pub fn make_oxide_comb(slice: usize, lut: usize) -> Bel {
        let ch = Z_TO_CHAR[slice];
        let postfix = format!("SLICE{}", ch);
        let mut pins = vec![
            input_m!(&postfix, "A", &format!("A{}", lut), "LUT A input"),
            input_m!(&postfix, "B", &format!("B{}", lut), "LUT B input"),
            input_m!(&postfix, "C", &format!("C{}", lut), "LUT C input"),
            input_m!(&postfix, "D", &format!("D{}", lut), "LUT D input"),
            input_m!(
                &postfix,
                "FCI",
                if lut == 0 { "FCI" } else { "INT_CARRY" },
                "CCU2 fast carry input"
            ),
            output_m!(&postfix, "F", &format!("F{}", lut), "LUT/sum output"),
            output_m!(
                &postfix,
                "FCO",
                if lut == 1 { "FCO" } else { "INT_CARRY" },
                "CCU2 fast carry output"
            ),
        ];
        if lut == 0 {
            // MUX2 in LUT0 COMB only
            pins.append(&mut vec![
                input!(&postfix, "SEL", "MUX2 select input"),
                input!(&postfix, "F1", "input from second LUT to MUX2"),
                output_m!(&postfix, "OFX", "OFX0", "MUX2 output"),
            ]);
        }
        if slice == 0 || slice == 1 {
            // DPRAM in lower two SLICEs only
            pins.append(&mut vec![
                input!(&postfix, "WAD0", "LUTRAM write address 0 (from RAMW)"),
                input!(&postfix, "WAD1", "LUTRAM write address 1 (from RAMW)"),
                input!(&postfix, "WAD2", "LUTRAM write address 2 (from RAMW)"),
                input!(&postfix, "WAD3", "LUTRAM write address 3 (from RAMW)"),
                input_m!(
                    &postfix,
                    "WDI",
                    &format!("WDI{}", lut),
                    "LUTRAM write data (from RAMW)"
                ),
                input!(&postfix, "WCK", "LUTRAM write clock (from RAMW)"),
                input!(&postfix, "WRE", "LUTRAM write enable (from RAMW)"),
            ]);
        }
        Bel {
            name: format!("{}_LUT{}", &postfix, lut),
            beltype: String::from("OXIDE_COMB"),
            pins: pins,
            rel_x: 0,
            rel_y: 0,
            z: (slice << 3 | lut) as u32,
        }
    }

    pub fn make_oxide_ramw(slice: usize) -> Bel {
        assert_eq!(slice, 2);
        let ch = Z_TO_CHAR[slice];
        let postfix = format!("SLICE{}", ch);
        let pins = vec![
            input!(&postfix, "A0", "buffered to WADO3"),
            input!(&postfix, "A1", "buffered to WDO2"),
            input!(&postfix, "B0", "buffered to WADO1"),
            input!(&postfix, "B1", "buffered to WDO3"),
            input!(&postfix, "C0", "buffered to WADO2"),
            input!(&postfix, "C1", "buffered to WDO1"),
            input!(&postfix, "D0", "buffered to WADO0"),
            input!(&postfix, "D1", "buffered to WDO0"),
            input!(&postfix, "CLK", "buffered to WCKO"),
            input!(&postfix, "LSR", "buffered to WREO"),
            output!(&postfix, "WADO0", "LUTRAM write address 0 (to SLICEA/B)"),
            output!(&postfix, "WADO1", "LUTRAM write address 1 (to SLICEA/B)"),
            output!(&postfix, "WADO2", "LUTRAM write address 2 (to SLICEA/B)"),
            output!(&postfix, "WADO3", "LUTRAM write address 3 (to SLICEA/B)"),
            output!(&postfix, "WCKO", "LUTRAM write clock (to SLICEA/B)"),
            output!(&postfix, "WREO", "LUTRAM write enable (to SLICEA/B)"),
            output!(&postfix, "WDO0", "LUTRAM write data 0 (to SLICEA)"),
            output!(&postfix, "WDO1", "LUTRAM write data 1 (to SLICEA)"),
            output!(&postfix, "WDO2", "LUTRAM write data 2 (to SLICEB)"),
            output!(&postfix, "WDO3", "LUTRAM write data 3 (to SLICEB)"),
        ];
        Bel {
            name: format!("{}_RAMW", &postfix),
            beltype: String::from("RAMW"),
            pins: pins,
            rel_x: 0,
            rel_y: 0,
            z: (slice << 3 | 4) as u32,
        }
    }

    pub fn make_seio33(z: usize) -> Bel {
        let ch = Z_TO_CHAR[z];
        let postfix = format!("SEIO33_CORE_IO{}", ch);
        Bel {
            name: format!("PIO{}", ch),
            beltype: String::from("SEIO33_CORE"),
            pins: vec![
                inout_m!(&postfix, "B", "PAD", "top level pad signal"),
                input_m!(
                    &postfix,
                    "I",
                    "PADDO",
                    "output buffer input from fabric/IOLOGIC"
                ),
                input_m!(
                    &postfix,
                    "T",
                    "PADDT",
                    "output buffer tristate (0=driven, 1=hi-z)"
                ),
                output_m!(
                    &postfix,
                    "O",
                    "PADDI",
                    "input buffer output to fabric/IOLOGIC"
                ),
                input!(&postfix, "I3CRESEN", "I3C strong pullup enable"),
                input!(&postfix, "I3CWKPU", "I3C weak pullup enable"),
            ],
            rel_x: 0,
            rel_y: 0,
            z: z as u32,
        }
    }

    pub fn make_seio18(z: usize) -> Bel {
        let ch = Z_TO_CHAR[z];
        let postfix = if z == 1 {
            format!("SEIO18_CORE_IO{}", ch)
        } else {
            format!("DIFFIO18_CORE_IO{}", ch)
        };
        Bel {
            name: format!("PIO{}", ch),
            beltype: String::from("SEIO18_CORE"),
            pins: vec![
                inout_m!(&postfix, "B", "IOPAD", "top level pad signal"),
                input_m!(
                    &postfix,
                    "I",
                    "PADDO",
                    "output buffer input from fabric/IOLOGIC"
                ),
                input_m!(
                    &postfix,
                    "T",
                    "PADDT",
                    "output buffer tristate (0=driven, 1=hi-z)"
                ),
                output_m!(
                    &postfix,
                    "O",
                    "PADDI",
                    "input buffer output to fabric/IOLOGIC"
                ),
                input!(&postfix, "DOLP", "DPHY LP mode output buffer input"),
                output!(&postfix, "INLP", "DPHY LP mode input buffer output"),
                output!(&postfix, "INADC", "analog signal out to ADC"),
            ],
            rel_x: 0,
            rel_y: 0,
            z: z as u32,
        }
    }

    pub fn make_diffio18() -> Bel {
        let postfix = format!("DIFFIO18_CORE_IOA");
        Bel {
            name: format!("DIFFIO18"),
            beltype: String::from("DIFFIO18_CORE"),
            pins: vec![
                inout_m!(&postfix, "B", "IOPAD", "top level pad signal"),
                input_m!(
                    &postfix,
                    "I",
                    "PADDO",
                    "output buffer input from fabric/IOLOGIC"
                ),
                input_m!(
                    &postfix,
                    "T",
                    "PADDT",
                    "output buffer tristate (0=driven, 1=hi-z)"
                ),
                output_m!(
                    &postfix,
                    "O",
                    "PADDI",
                    "input buffer output to fabric/IOLOGIC"
                ),
                input!(&postfix, "DOLP", "DPHY LP mode output buffer input"),
                input!(&postfix, "HSRXEN", "DPHY high-speed receiver enable"),
                input!(&postfix, "HSTXEN", "DPHY high-speed transmitter enable"),
                output!(&postfix, "INLP", "DPHY LP mode input buffer output"),
                output!(&postfix, "INADC", "analog signal out to ADC"),
            ],
            rel_x: 0,
            rel_y: 0,
            z: 2,
        }
    }

    pub fn make_osc_core() -> Bel {
        let postfix = format!("OSC_CORE");
        Bel {
            name: format!("OSC_CORE"),
            beltype: String::from("OSC_CORE"),
            pins: vec![
                output!(&postfix, "HFCLKOUT", "HF oscillator output"),
                output!(&postfix, "LFCLKOUT", "LF oscillator output"),
                input!(&postfix, "HFOUTEN", "HF oscillator output enable"),
                input!(&postfix, "HFTRMFAB8", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB7", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB6", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB5", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB4", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB3", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB2", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB1", "HF oscillator trimming"),
                input!(&postfix, "HFTRMFAB0", "HF oscillator trimming"),
                input!(&postfix, "LFTRMFAB8", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB7", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB6", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB5", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB4", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB3", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB2", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB1", "LF oscillator trimming"),
                input!(&postfix, "LFTRMFAB0", "LF oscillator trimming"),
                input!(&postfix, "HFSDSCEN", "HF oscillator SEDSEC output enable"),
                output!(&postfix, "HFCLKCFG", "HF oscillator config output"),
                output!(&postfix, "HFSDCOUT", "HF oscillator SEDSEC output"),
            ],
            rel_x: 0,
            rel_y: 1,
            z: 0,
        }
    }

    pub fn make_ebr(tiledata: &TileBitsDatabase, z: usize) -> Bel {
        Bel {
            name: format!("EBR{}", z),
            beltype: format!("OXIDE_EBR"),
            pins: Bel::get_io(&tiledata, "_EBR_CORE", -1, -1),
            rel_x: -1,
            rel_y: -1,
            z: z as u32,
        }
    }

    pub fn make_dsp(tiledata: &TileBitsDatabase, name: &str, beltype: &str, x: i32, y: i32, z: usize) -> Bel {
        Bel {
            name: name.to_string(),
            beltype: beltype.to_string(),
            pins: Bel::get_io(&tiledata, &format!("_{}_{}", &beltype, &name), x, y),
            rel_x: x,
            rel_y: y,
            z: z as u32,
        }
    }

    pub fn make_dcc(side: &str, z: usize) -> Bel {
        let postfix = format!("DCC_DCC{}", z);
        let rel_x = match side {
            "R" => -1,
            _ => 0,
        };
        let rel_y = match side {
            "C" => -1,
            _ => 0,
        };
        Bel {
            name: format!("DCC_{}{}", side, z),
            beltype: format!("DCC"),
            pins: vec![
                input!(&postfix, "CLKI", "DCC clock input"),
                input!(&postfix, "CE", "DCC clock enable"),
                output!(&postfix, "CLKO", "DCC clock output"),
            ],
            rel_x: rel_x,
            rel_y: rel_y,
            z: z as u32,
        }
    }

    pub fn make_vcc() -> Bel {
        Bel {
            name: format!("VCC_DRV"),
            beltype: format!("VCC_DRV"),
            pins: vec![
                BelPin::new("Z", "global Vcc net access", PinDir::OUTPUT, "G:VCC", 0, 0)
            ],
            rel_x: 0,
            rel_y: 0,
            z: 16,
        }
    }

    pub fn make_pll_core(name: &str, tiledata: &TileBitsDatabase, rel_x: i32, rel_y: i32) -> Bel {
        Bel {
            name: name.to_string(),
            beltype: "PLL_CORE".to_string(),
            pins: Bel::get_io(&tiledata, "_PLL_CORE_I_PLL_LMMI", rel_x, rel_y),
            rel_x: rel_x,
            rel_y: rel_y,
            z: 0,
        }
    }

    pub fn make_lram_core(name: &str, tiledata: &TileBitsDatabase, rel_x: i32, rel_y: i32) -> Bel {
        Bel {
            name: name.to_string(),
            beltype: "LRAM_CORE".to_string(),
            pins: Bel::get_io(&tiledata, "_LRAM_CORE", rel_x, rel_y),
            rel_x: rel_x,
            rel_y: rel_y,
            z: 0,
        }
    }

    pub fn make_dphy_core(name: &str, tiledata: &TileBitsDatabase, rel_x: i32, rel_y: i32) -> Bel {
        Bel {
            name: name.to_string(),
            beltype: "DPHY_CORE".to_string(),
            pins: Bel::get_io(&tiledata, "_DPHY_CORE_DPHY0", rel_x, rel_y),
            rel_x: rel_x,
            rel_y: rel_y,
            z: 0,
        }
    }
}

pub fn get_tile_bels(tiletype: &str, tiledata: &TileBitsDatabase) -> Vec<Bel> {
    let mut stt = tiletype;
    if tiletype.ends_with("_EVEN") || tiletype.ends_with("_ODD") {
        stt = &tiletype[0..tiletype.rfind('_').unwrap()];
    }
    match stt {
        "PLC" => (0..4)
            .map(|slice| {
                let mut bels = vec![
                    Bel::make_oxide_comb(slice, 0),
                    Bel::make_oxide_comb(slice, 1),
                    Bel::make_oxide_ff(slice, 0),
                    Bel::make_oxide_ff(slice, 1),
                ];
                if slice == 2 {
                    bels.push(Bel::make_oxide_ramw(slice));
                }
                bels
            })
            .flatten()
            .collect(),
        "SYSIO_B0_0" | "SYSIO_B1_0" | "SYSIO_B1_0_C" | "SYSIO_B2_0" | "SYSIO_B2_0_C"
        | "SYSIO_B6_0" | "SYSIO_B6_0_C" | "SYSIO_B7_0" | "SYSIO_B7_0_C"
        | "SYSIO_B0_0_15K" | "SYSIO_B1_0_15K" => {
            (0..2).map(Bel::make_seio33).collect()
        },
        "SYSIO_B1_DED" | "SYSIO_B1_DED_15K" => vec![Bel::make_seio33(1)],
        "SYSIO_B3_0" | "SYSIO_B3_0_DLY30_V18" | "SYSIO_B3_0_DQS1" | "SYSIO_B3_0_DQS3"
        | "SYSIO_B4_0" | "SYSIO_B4_0_DQS1" | "SYSIO_B4_0_DQS3" | "SYSIO_B4_0_DLY50" | "SYSIO_B4_0_DLY42"
        |  "SYSIO_B5_0" | "SYSIO_B5_0_15K_DQS52" | "SYSIO_B4_0_15K_DQS42"
        | "SYSIO_B4_0_15K_BK4_V42" | "SYSIO_B4_0_15K_V31" | "SYSIO_B3_0_15K_DQS32" => vec![Bel::make_seio18(0), Bel::make_seio18(1), Bel::make_diffio18()],
        "EFB_1_OSC" | "OSC_15K" => vec![Bel::make_osc_core()],
        "EBR_1" => vec![Bel::make_ebr(&tiledata, 0)],
        "EBR_4" => vec![Bel::make_ebr(&tiledata, 1)],
        "EBR_7" => vec![Bel::make_ebr(&tiledata, 2)],
        "EBR_9" => vec![Bel::make_ebr(&tiledata, 3)],
        "DSP_R_1" | "DSP_L_1" => vec![
            Bel::make_dsp(&tiledata, "PREADD9_L0", "PREADD9_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "PREADD9_H0", "PREADD9_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "MULT9_L0", "MULT9_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "MULT9_H0", "MULT9_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18_0", "MULT18_CORE", 0, -1, 4),
        ],
        "DSP_R_2" | "DSP_L_2" => vec![
            Bel::make_dsp(&tiledata, "PREADD9_L1", "PREADD9_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "PREADD9_H1", "PREADD9_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "MULT9_L1", "MULT9_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "MULT9_H1", "MULT9_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18_1", "MULT18_CORE", 0, -1, 4),
        ],
        "DSP_R_3" | "DSP_L_3" => vec![
            Bel::make_dsp(&tiledata, "REG18_L0_0", "REG18_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "REG18_L0_1", "REG18_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "REG18_L1_0", "REG18_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "REG18_L1_1", "REG18_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18X36_0", "MULT18X36_CORE", 0, -1, 4),
            Bel::make_dsp(&tiledata, "ACC54_0", "ACC54_CORE", 0, -1, 5),
        ],
        "DSP_R_5" | "DSP_L_5" => vec![
            Bel::make_dsp(&tiledata, "PREADD9_L2", "PREADD9_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "PREADD9_H2", "PREADD9_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "MULT9_L2", "MULT9_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "MULT9_H2", "MULT9_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18_2", "MULT18_CORE", 0, -1, 4),
        ],
        "DSP_R_6" | "DSP_L_6" => vec![
            Bel::make_dsp(&tiledata, "PREADD9_L3", "PREADD9_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "PREADD9_H3", "PREADD9_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "MULT9_L3", "MULT9_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "MULT9_H3", "MULT9_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18_3", "MULT18_CORE", 0, -1, 4),
        ],
        "DSP_R_7" | "DSP_L_7" => vec![
            Bel::make_dsp(&tiledata, "REG18_H0_0", "REG18_CORE", 0, -1, 0),
            Bel::make_dsp(&tiledata, "REG18_H0_1", "REG18_CORE", 0, -1, 1),
            Bel::make_dsp(&tiledata, "REG18_H1_0", "REG18_CORE", 0, -1, 2),
            Bel::make_dsp(&tiledata, "REG18_H1_1", "REG18_CORE", 0, -1, 3),
            Bel::make_dsp(&tiledata, "MULT18X36_1", "MULT18X36_CORE", 0, -1, 4),
            Bel::make_dsp(&tiledata, "ACC54_1", "ACC54_CORE", 0, -1, 5),
            Bel::make_dsp(&tiledata, "MULT36", "MULT36_CORE", 0, -1, 6),
        ],

        "CIB_T" => vec![Bel::make_vcc()],

        "LMID" | "LMID_RBB_5_15K" => (0..12).map(|x| Bel::make_dcc("L", x)).collect(),
        "RMID_DLY20" | "RMID_PICB_DLY10" => (0..12).map(|x| Bel::make_dcc("R", x)).collect(),
        "TMID_0" => (0..16).map(|x| Bel::make_dcc("T", x)).collect(),
        "BMID_0_ECLK_1" => (0..18).map(|x| Bel::make_dcc("B", x)).collect(),
        "CMUX_0" => (0..4).map(|x| Bel::make_dcc("C", x)).collect(),
        "GPLL_LLC" => vec![Bel::make_pll_core("PLL_LLC", &tiledata, 1, 0)],
        "GPLL_ULC" => vec![Bel::make_pll_core("PLL_ULC", &tiledata, 0, 1)],
        "GPLL_LRC" => vec![Bel::make_pll_core("PLL_LRC", &tiledata, -1, 0)],
        "LRAM_0" => vec![Bel::make_lram_core("LRAM0", &tiledata, -1, -5)],
        "LRAM_1" => vec![Bel::make_lram_core("LRAM1", &tiledata, -1, -1)],

        "LRAM_0_15K" => vec![Bel::make_lram_core("LRAM0", &tiledata, -1, 0)],
        "LRAM_1_15K" => vec![Bel::make_lram_core("LRAM1", &tiledata, -1, 0)],
        "LRAM_2_15K" => vec![Bel::make_lram_core("LRAM2", &tiledata, 0, -1)],
        "LRAM_3_15K" => vec![Bel::make_lram_core("LRAM3", &tiledata, 0, -1)],
        "LRAM_4_15K" => vec![Bel::make_lram_core("LRAM4", &tiledata, 0, -1)],

        "MIPI_DPHY_0" => vec![Bel::make_dphy_core("TDPHY_CORE2", &tiledata, -2, 0)],
        "MIPI_DPHY_1" => vec![Bel::make_dphy_core("TDPHY_CORE26", &tiledata, -2, 0)],
        _ => vec![],
    }
}

// Get the tiles that a bel's configuration might be split across
pub fn get_bel_tiles(chip: &Chip, tile: &Tile, bel: &Bel) -> Vec<String> {
    let tn = tile.name.to_string();
    let rel_tile = |dx: i32, dy: i32, tt: &str| {
        chip.tile_by_xy_type((tile.x as i32 + dx).try_into().unwrap(),
            (tile.y as i32 + dy).try_into().unwrap(), tt.clone()).unwrap().name.to_string()
    };

    let rel_tile_prefix = |dx, dy, tt_prefix| {
        for tile in chip.tiles_by_xy(tile.x + dx, tile.y + dy).iter() {
            if tile.tiletype.starts_with(tt_prefix) {
                return tile.name.to_string();
            }
        }
        panic!("no tile matched prefix ({}, {}, {})", tile.x + dx, tile.y + dy, tt_prefix);
    };
    let rel_tile_suffix = |dx, dy, tt_suffix| {
        for tile in chip.tiles_by_xy(tile.x + dx, tile.y + dy).iter() {
            if tile.tiletype.ends_with(tt_suffix) {
                return tile.name.to_string();
            }
        }
        panic!("no tile matched suffix ({}, {}, {})", tile.x + dx, tile.y + dy, tt_suffix);
    };

    let tt = &tile.tiletype[..];
    match &bel.beltype[..] {
        "SEIO33_CORE" => match tt {
            "SYSIO_B1_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B1_0_REM")],
            "SYSIO_B2_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B2_0_REM")],
            "SYSIO_B6_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B6_0_REM")],
            "SYSIO_B7_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B7_0_REM")],
            "SYSIO_B1_0_15K" => match &tile.name[..] {
                "CIB_R9C75:SYSIO_B1_0_15K" => vec![tn, rel_tile(0, 1, "RMID_PICB_DLY10")], // irregular special case...
                _ => vec![tn, rel_tile(0, 1, "SYSIO_B1_1_15K")],
            }
            _ => vec![tn]
        }
        "SEIO18_CORE" | "DIFF18_CORE" => vec![tn, rel_tile_prefix(1, 0, "SYSIO")],
        "OXIDE_EBR" => match bel.z {
            0 => vec![rel_tile(0, 0, "EBR_1"), rel_tile(1, 0, "EBR_2")],
            1 => vec![rel_tile(0, 0, "EBR_4"), rel_tile(1, 0, "EBR_5")],
            2 => vec![rel_tile(0, 0, "EBR_7"), rel_tile(1, 0, "EBR_8")],
            3 => vec![rel_tile(0, 0, "EBR_9"), rel_tile_suffix(1, 0, "EBR_10")],
            _ => panic!("unknown EBR z-index")
        }
        "PREADD9_CORE" | "MULT9_CORE" | "MULT18_CORE" | "REG18_CORE" |
        "MULT18X36_CORE" | "MULT36_CORE" | "ACC54_CORE" => {
            let split_tile: Vec<&str> = tile.tiletype.split('_').collect();
            let offset = split_tile[2].parse::<i32>().unwrap();
            match split_tile[1] {
                "L" => (0..11).map(|x| rel_tile(x - offset, 0, &format!("DSP_L_{}", x))).collect(),
                "R" => (1..12).map(|x| rel_tile(x - offset, 0, &format!("DSP_R_{}", x))).collect(),
                _ => panic!("bad DSP tile {}", &tile.tiletype)
            }
        }
        _ => vec![tn]
    }
}
