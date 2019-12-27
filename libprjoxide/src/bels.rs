// A reference to a wire in a relatively located tile
struct RelWire {
    rel_x: i32,   // (bel.x + rel_x == tile.x)
    rel_y: i32,   // (bel.y + rel_y == tile.y)
    name: String, // wire name in tile
}

enum PinDir {
    INPUT,
    OUTPUT,
    INOUT,
}

struct BelPin {
    name: String,  // name of pin on bel
    desc: String,  // description for documentation
    dir: PinDir,   // direction
    wire: RelWire, // reference to wire in tile
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
}

struct Bel {
    name: String,
    beltype: String,
    pins: Vec<BelPin>,
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

impl Bel {
    pub fn make_slice(z: char) -> Bel {
        let postfix = format!("SLICE{}", z);
        let mut pins = vec![
            input!(&postfix, "A0", "LUT0 A input"),
            input!(&postfix, "A1", "LUT1 A input"),
            input!(&postfix, "B0", "LUT0 B input"),
            input!(&postfix, "B1", "LUT1 B input"),
            input!(&postfix, "C0", "LUT0 C input"),
            input!(&postfix, "C1", "LUT1 C input"),
            input!(&postfix, "D0", "LUT0 D input"),
            input!(&postfix, "D1", "LUT1 D input"),
            input!(&postfix, "M0", "FF0 M (direct) input"),
            input!(&postfix, "M1", "FF1 M (direct) input"),
            input!(&postfix, "DI0", "FF0 DI (LUT/mux output) input"),
            input!(&postfix, "DI1", "FF1 DI (LUT output) input"),
            input!(&postfix, "SEL", "LUT MUX2 select input"),
            input!(&postfix, "FCI", "fast carry input"),
            input!(&postfix, "CLK", "FF clock"),
            input!(&postfix, "CE", "FF clock enable"),
            input!(&postfix, "LSR", "FF local set/reset"),
            output!(&postfix, "F0", "LUT0 output"),
            output!(&postfix, "F1", "LUT1 output"),
            output!(&postfix, "Q0", "FF0 output"),
            output!(&postfix, "Q1", "FF1 output"),
            output!(&postfix, "OFX0", "MUX2 output"),
            output!(&postfix, "FCO", "fast carry out"),
        ];
        match z {
            'A' | 'B' => {
                pins.append(&mut vec![
                    input!(&postfix, "WAD0", "LUTRAM write address 0 (from SLICEC)"),
                    input!(&postfix, "WAD1", "LUTRAM write address 1 (from SLICEC)"),
                    input!(&postfix, "WAD2", "LUTRAM write address 2 (from SLICEC)"),
                    input!(&postfix, "WAD3", "LUTRAM write address 3 (from SLICEC)"),
                    input!(&postfix, "WCK", "LUTRAM write clock (from SLICEC)"),
                    input!(&postfix, "WRE", "LUTRAM write enable (from SLICEC)"),
                    input!(&postfix, "WDI0", "LUTRAM write data 0"),
                    input!(&postfix, "WDI1", "LUTRAM write data 1"),
                ]);
            }
            'C' => {
                pins.append(&mut vec![
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
                ]);
            }
            _ => {}
        }
        Bel {
            name: postfix.clone(),
            beltype: String::from("SLICE"),
            pins: pins,
        }
    }
}
