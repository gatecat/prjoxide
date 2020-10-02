use crate::chip::*;
use crate::database::TileBitsDatabase;

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

        for src_wire in db.get_source_wires() {
            add_wire(&src_wire, PinDir::OUTPUT);
        }

        for sink_wire in db.get_sink_wires() {
            add_wire(&sink_wire, PinDir::INPUT);
        }
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
                    "WD",
                    &format!("WD{}", lut),
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

    pub fn make_osc_core() -> Bel {
        let postfix = format!("OSC_CORE");
        Bel {
            name: format!("OSC_CORE"),
            beltype: String::from("OSC_CORE"),
            pins: vec![
                output!(&postfix, "HFCLKOUT", "HF oscillator output"),
                output!(&postfix, "LFCLKOUT", "LF oscillator output"),
                input!(&postfix, "HFOUTEN", "HF oscillator output enable"),
            ],
            rel_x: 0,
            rel_y: 1,
            z: 0,
        }
    }

    pub fn make_ebr(tiledata: &TileBitsDatabase, z: usize) -> Bel {
        Bel {
            name: format!("EBR_CORE"),
            beltype: format!("OXIDE_EBR"),
            pins: Bel::get_io(&tiledata, "_EBR_CORE", -1, -1),
            rel_x: -1,
            rel_y: -1,
            z: z as u32,
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
        | "SYSIO_B6_0" | "SYSIO_B6_0_C" | "SYSIO_B7_0" | "SYSIO_B7_0_C" => {
            (0..2).map(Bel::make_seio33).collect()
        }
        "SYSIO_B3_0" | "SYSIO_B4_0" | "SYSIO_B5_0" => (0..2).map(Bel::make_seio18).collect(),
        "EFB_1_OSC" => vec![Bel::make_osc_core()],
        "EBR_1" => vec![Bel::make_ebr(&tiledata, 0)],
        "EBR_4" => vec![Bel::make_ebr(&tiledata, 1)],
        "EBR_7" => vec![Bel::make_ebr(&tiledata, 2)],
        "EBR_8" => vec![Bel::make_ebr(&tiledata, 3)],
        _ => vec![],
    }
}

// Get the tiles that a bel's configuration might be split across
pub fn get_bel_tiles(chip: &Chip, tile: &Tile, bel: &Bel) -> Vec<String> {
    let tn = tile.name.to_string();
    let rel_tile = |dx, dy, tt| {
        chip.tile_by_xy_type(tile.x + dx, tile.y + dy, tt).unwrap().tiletype.to_string()
    };

    let rel_tile_prefix = |dx, dy, tt_prefix| {
        for tile in chip.tiles_by_xy(tile.x + dx, tile.y + dy).iter() {
            if tile.name.starts_with(tt_prefix) {
                return tile.tiletype.to_string();
            }
        }
        panic!("no tile matched prefix");
    };

    let tt = &tile.tiletype[..];
    match &bel.beltype[..] {
        "SEIO33_CORE" => match tt {
            "SYSIO_B1_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B1_0_REM")],
            "SYSIO_B2_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B2_0_REM")],
            "SYSIO_B6_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B6_0_REM")],
            "SYSIO_B7_0_C" => vec![tn, rel_tile(0, 1, "SYSIO_B7_0_REM")],
            _ => vec![tn]
        }
        "SEIO18_CORE" | "DIFF18_CORE" => vec![tn, rel_tile_prefix(1, 0, "SYSIO")],
        "OXIDE_EBR" => match bel.z {
            0 => vec![rel_tile(0, 0, "EBR_1"), rel_tile(1, 0, "EBR_2")],
            1 => vec![rel_tile(0, 0, "EBR_4"), rel_tile(1, 0, "EBR_5")],
            2 => vec![rel_tile(0, 0, "EBR_7"), rel_tile(1, 0, "EBR_8")],
            3 => vec![rel_tile(0, 0, "EBR_8"), rel_tile(1, 0, "EBR_9")],
            _ => panic!("unknown EBR z-index")
        }
        _ => vec![tn]
    }
}
