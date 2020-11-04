use crate::bels::*;

// Function to classify a pip for timing purposes
pub fn classify_pip(src_x: i32, src_y: i32, src_name: &str, dst_x: i32, dst_y: i32, dst_name: &str) -> Option<String> {
    static WIRE_CLASSES: &[(&'static str, &'static str)] = &[
        ("JA?", "a"),
        ("JB?", "b"),
        ("JC?", "c"),
        ("JD?", "d"),
        ("JM?", "m"),
        ("JCLK?", "clk"),
        ("JCE?", "ce"),
        ("JLSR?", "lsr"),
        ("JF?", "f"),
        ("JQ?", "q"),

        ("V00?0?00", "span0v"),
        ("H00?0?00", "span0h"),
        ("V01S0?00", "span1s"),
        ("H01W0?00", "span1w"),

        ("V02N0?01", "span2v"),
        ("V02S0?01", "span2s"),
        ("H02W0?01", "span2w"),
        ("H02E0?01", "span2e"),

        ("V06N0?03", "span6v"),
        ("V06S0?03", "span6s"),
        ("H06W0?03", "span6w"),
        ("H06E0?03", "span6e"),

        ("JA?_SLICE?", "a_lut"),
        ("JB?_SLICE?", "b_lut"),
        ("JCIN?_CDMUX", "c_lut"),

        ("JD?_DRMUX", "d_drmux"),
        ("JC?_DRMUX", "c_drmux"),
        ("JF?_DRMUX", "f_drmux"),

        ("JM?_DIMUX", "m_dimux"),
        ("JD?_DIMUX", "d_dimux"),

        ("JF?_SLICE?", "f_lut"),
        ("JOFX?_SLICE?", "ofx"),

        ("JDI?_SLICE?", "di_dff"),
        ("JQ?_SLICE?", "q_dff"),
        ("JCLK_SLICE?", "clk_dff"),
        ("JLSR_SLICE?", "lsr_dff"),
        ("JCE_SLICE?", "ce_dff"),

        // ("JCIBMUXINA?", "a_cibmuxi"),
        // ("JCIBMUXINB?", "b_cibmuxi"),
        // ("JCIBMUXINC?", "c_cibmuxi"),
        // ("JCIBMUXIND?", "d_cibmuxi"),

        // ("JCIBMUXOUTA?", "a_cibmuxo"),
        // ("JCIBMUXOUTB?", "b_cibmuxo"),
        // ("JCIBMUXOUTC?", "c_cibmuxo"),
        // ("JCIBMUXOUTD?", "d_cibmuxo"),

        ("JCIBMUXIN??", "cibmuxi"),
        ("JCIBMUXOUT??", "cibmuxo"),

        ("HPBX0?00", "hpbx"),
        ("VPSX0?00", "vpsx"),
        ("HPRX0?00", "hprx"),
        ("?HPRX?", "hprx_g"),
        ("?HPRX??", "hprx_g"),
        ("JHPRX?_CMUX_CORE_CMUX?", "hprx_cmux"),
        ("JHPRX??_CMUX_CORE_CMUX?", "hprx_cmux"),
    ];

    static CIB_PRIMS: &[(&'static str, &'static str)] = &[
        ("_EBR_CORE", "ebr"),
        ("_IOLOGIC_CORE_", "iologic"),
        ("_SIOLOGIC_CORE_", "siologic"),
        ("_DIFFIO18_CORE_", "io18"),
        ("_SEIO18_CORE_", "io18"),
        ("_SEIO33_CORE_", "io33"),
        ("_MULT9_CORE_", "mult9"),
        ("_PREADD9_CORE_", "preadd9"),
        ("_MULT18X36_CORE_", "mult18x36"),
        ("_MULT18_CORE_", "mult18"),
        ("_REG18_CORE_", "reg18"),
        ("_ACC54_CORE_", "acc54"),
        ("_MULT36_CORE_", "mult36"),
        ("_LRAM_CORE", "lram"),
        ("_PLL_CORE_", "pll"),
        ("_CONFIG_", "cfg"),
        ("_DCC_", "dcc"),
        ("_DCS_", "dcs"),
    ];

    static DSP_PRIMS: &[&'static str] = &["mult9", "preadd9", "mult18x36", "mult18", "reg18", "acc54", "mult36"];

    let get_wire_class = |wire: &str| {
        for (pattern, cls) in WIRE_CLASSES {
            if pattern.len() != wire.len() {
                continue
            }
            if pattern.chars().zip(wire.chars()).all(|(p, c)| p == '?' || p == c) {
                return Some(cls)
            }
        }
        None
    };

    let get_cib_prim = |wire: &str| {
        CIB_PRIMS.iter().find_map(|(pat, cls)| if wire.contains(pat) {
            Some(cls)
        } else {
            None
        })
    };

    let src_wire_cls = get_wire_class(src_name);
    let dst_wire_cls = get_wire_class(dst_name);
    if src_wire_cls.is_some() && dst_wire_cls.is_some() {
        // Standard case of two classified wires
        let src_cls = src_wire_cls.unwrap();
        if src_cls == &"hpbx" || src_cls == &"vpsx" || src_cls == &"hprx" || src_cls == &"hprx_g" || src_cls == &"hprx_cmux" {
             return Some(format!("{} -> {}", src_cls, dst_wire_cls.unwrap()));
        } else {
            return Some(format!("{}{} -> {}",
                RelWire::prefix(src_x - dst_x, src_y - dst_y).to_lowercase(), src_cls, dst_wire_cls.unwrap()));
        }

    }

    let src_prim = get_cib_prim(src_name);
    let dst_prim = get_cib_prim(dst_name);

    // Interconnect to/from CIBs
    if src_prim.is_some() && dst_wire_cls.is_some() {
        return Some(format!("{} -> {}", src_prim.unwrap(), dst_wire_cls.unwrap()))
    } else if src_wire_cls.is_some() && dst_prim.is_some() {
        return Some(format!("{} -> {}", src_wire_cls.unwrap(), dst_prim.unwrap()))
    }

    // Special cases - logic
    if src_name.contains("_SLICE") || dst_name.contains("_SLICE") || src_name.ends_with("CDMUX") || dst_name.ends_with("DIMUX") ||  dst_name.ends_with("DRMUX") {
        if dst_name.starts_with("JW") {
            return Some("lutram_internal".to_string());
        }
        return Some("slice_internal".to_string());
    } else if src_name == "JFCOUT" && dst_name == "HFIE0000" {
        return Some("tile_carry".to_string());
    }
    // Internal block routing
    if src_prim.is_some() && dst_prim.is_some() {

        let sp = src_prim.unwrap();
        let dp = dst_prim.unwrap();

        if DSP_PRIMS.contains(sp) {
            // DSP route-thrus
            let postfix1 = src_name.splitn(2, '_').nth(1).unwrap();
            let postfix2 = dst_name.splitn(2, '_').nth(1).unwrap();
            if postfix1 == postfix2 {
                // Is a route-thru, as both sides of the PIP are the same primitive
                return Some(format!("{}_routethru", sp));
            }
        }

        if sp == dp {
            return Some(format!("{}_internal", sp));
        } else {
            return Some(format!("{} -> {}", sp, dp));
        }
    }

    // These are a useful zero-delay hint to the solver; if seemingly meaningless otherwise
    if src_name.contains("VCC") && dst_wire_cls.is_some() {
        return Some(format!("vcc -> {}", dst_wire_cls.unwrap()));
    }
    if (src_name.contains("VCC") && dst_name.contains("VCC")) || src_name.contains("VHI") {
        return Some("vcc_internal".to_string());
    }
    // Global clock routing
    if src_name.contains("MIDMUX") && dst_name.contains("MIDMUX") {
        if dst_name.starts_with("JVPF") || dst_name.starts_with("JHPF") {
            let clksource = src_name.splitn(2, '_').nth(0).unwrap().to_lowercase();
            return Some(format!("{} -> {}_mid", clksource, dst_name[0..4].to_lowercase()));
        }
    }
    if src_name.contains("MIDMUX") && dst_name.contains("DCC") {
        return Some("mid -> dcc".to_string());
    }
    if dst_name.contains("MIDMUX") && !src_name.contains("MIDMUX") {
        let clksource = dst_name.splitn(2, '_').nth(0).unwrap().to_lowercase();
        return Some(format!("{}_mid_entry", clksource));
    }
    const DIGIT_OR_US: &[char] = &['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_'];
    if src_name.contains("_DCC_") && dst_name.contains("_CMUX_CORE_") {
        // From DCC to center mux
        let cmux_entry = dst_name.splitn(2, &DIGIT_OR_US[..]).nth(0).unwrap().to_lowercase();
        return Some(format!("dcc -> {}_cmux", cmux_entry));
    }
    if src_name.contains("_DCC_") && dst_name.contains("_DCSMUX_CORE_") {
        // From DCC to DCS
        let cmux_entry = dst_name.splitn(2, &DIGIT_OR_US[..]).nth(0).unwrap().to_lowercase();
        return Some(format!("dcc -> {}_dcs", cmux_entry));
    }
    if src_name.contains("DCSOUT") && dst_name.contains("_CMUX_CORE_") {
        return Some("dcs -> cmux".to_string());
    }
    if src_name.contains("_CMUX_CORE_") && dst_name.contains("_CMUX_CORE_") && dst_name.contains("JHPRX") {
        // Main center mux
        let cmux_node = src_name.splitn(2, &DIGIT_OR_US[..]).nth(0).unwrap().to_lowercase();
        return Some(format!("{}_cmux -> hprx_cmux", cmux_node));
    }
    None
}
