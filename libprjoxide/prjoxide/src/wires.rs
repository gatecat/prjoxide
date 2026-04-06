use log::warn;
// Wire normalisation for Nexus
use crate::chip::*;
use regex::Regex;

lazy_static! {
    //  - General wire name format
    static ref WIRE_RE: Regex = Regex::new(r"^R(\d+)C(\d+)_(.+)$").unwrap();
    //  - Global clock distribution levels
    // Horizontal branches
    static ref GLB_HBRANCH_RE: Regex = Regex::new(r"^HPBX(\d{2})00$").unwrap();
    // Vertical spine
    static ref GLB_SPINE_RE: Regex = Regex::new(r"^VPSX(\d{2})00$").unwrap();
    // Horizontal rows
    static ref GLB_HROW_RE: Regex = Regex::new(r"^HPRX(\d{2})00$").unwrap();
    // Horizontal row drivers
    static ref GLB_HROWD_RE: Regex = Regex::new(r"^([BT]?)([LR])HPRX(\d+)$").unwrap();
    // Central clock signals
    static ref GLB_CMUXI_RE: Regex = Regex::new(r"^J([HV])PF([NESW])(\d+)_(DCSMUX|CMUX)_CORE_(DCSMUX|CMUX)(\d)$").unwrap();
    // Perimeter clock signals
    static ref GLB_MIDMUX_RE: Regex = Regex::new(r"^(.*)(.)MID_CORE_(.)MIDMUX$").unwrap();
    // Edge clock signals
    static ref ECLK_RE: Regex = Regex::new(r"^JECLKOUT(\d)_ECLKCASMUX_CORE_ECLKCASMUX(\d+)$").unwrap();
    // Edge clock sources
    static ref ECLK_MUXIN_RE: Regex = Regex::new(r"^J(MUXIN(\d+)|[LU][LR]CLKO[PS]\d?|PCLK[TC]\d+)_ECLKBANK_CORE_ECLKBANK(\d+)$").unwrap();
    // Edge clock feedback
    static ref ECLK_FEEDBACK_RE: Regex = Regex::new(r"^J[LU][LR]CLKO[PS]\d?_ECLKLOGICMUXPLLFB_CORE_ECLKPLLFBR$").unwrap();
    // Edge clock to DDRDLL
    static ref ECLK_DDRDLL_RE: Regex = Regex::new(r"^JCLKOUT_ECLKDDR[RL]_\d$").unwrap();
    // DDR delay code signals
    static ref DLL_CODE_RE: Regex = Regex::new(r"^J(CODEI(\d+)_I_DQS_TOP_DLL_CODE_ROUTING_MUX|D[01]_I4_\d)$").unwrap();
    // DQS group shared signals
    static ref DQS_GROUP_RE: Regex = Regex::new(r"^J(WRPNTR\d|RDPNTR\d|DQSR90|DQSW270|DQSW)_DQSBUF(A?)_CORE_I_DQS_TOP$").unwrap();
    // Bank shared signals
    static ref BANK_VREF_RE: Regex = Regex::new(r"^JIVREFO_IVREF_CORE$").unwrap();

    // - CIB (general routing) regex
    static ref GENERAL_ROUTE_RE: Regex = Regex::new(r"R\d+C\d+_[VH]\d{2}[NESWTLBR]\d{4}").unwrap();
    static ref CIB_SIG_RE: Regex = Regex::new(r"R\d+C\d+_J?(CIBMUXOUT|CIBMUXIN)?[ABCDMFQ]\d").unwrap();
    static ref CIB_CTRLSIG_RE: Regex = Regex::new(r"R\d+C\d+_J?(CIBMUXOUT|CIBMUXIN)?(CLK|LSR|CE)\d").unwrap();
    static ref CIB_BOUNCE_RE: Regex = Regex::new(r"R\d+C\d+_[NESW]BOUNCE").unwrap();

    static ref H_WIRE_RE: Regex = Regex::new(r"^H(\d{2})([EW])(\d{2})(\d{2})$").unwrap();
    static ref V_WIRE_RE: Regex = Regex::new(r"^V(\d{2})([NS])(\d{2})(\d{2})$").unwrap();

}

fn is_full_global_wn(wire: &str) -> bool {
    GLB_HROWD_RE.is_match(wire)
        || GLB_CMUXI_RE.is_match(wire)
        || GLB_MIDMUX_RE.is_match(wire)
        || ECLK_RE.is_match(wire)
        || ECLK_MUXIN_RE.is_match(wire)
        || ECLK_FEEDBACK_RE.is_match(wire)
        || ECLK_DDRDLL_RE.is_match(wire)
        || DLL_CODE_RE.is_match(wire)
}

pub fn handle_edge_name(
    max_x: i32,
    max_y: i32,
    tx: i32,
    ty: i32,
    wx: i32,
    wy: i32,
    wn: &str,
) -> (String, i32, i32) {
    /*
    At the edges of the device, canonical wire names do not follow normal naming conventions, as they
    would mean the nominal position of the wire would be outside the bounds of the chip. Before we add routing to the
    database, we must however normalise these names to what they would be if not near the edges, otherwise there is a
    risk of database conflicts, having multiple names for the same wire.

    Returns a tuple (netname, x, y)
    */
    if let Some(hm) = H_WIRE_RE.captures(wn) {
        match &hm[1] {
            "01" => {
                // H01xyy00 --> x+1, H01xyy01
                if tx == max_x - 1 {
                    if hm[4].to_string() != "00" {
                        warn!("Invalid edge name {wn} - {hm:?}. hm[4] == '00'")
                    }
                    assert_eq!(hm[4].to_string(), "00");
                    return (format!("H01{}{}01", &hm[2], &hm[3]), wx + 1, wy);
                }
            }
            "02" => {
                if tx == 1 {
                    // H02E0002 --> x-1, H02E0001
                    // H02W0000 --> x-1, H02W00001
                    if &hm[2] == "E" && wx == 1 && &hm[4] == "02" {
                        return (format!("H02E{}01", &hm[3]), wx - 1, wy);
                    } else if &hm[2] == "W" && wx == 1 && &hm[4] == "00" {
                        return (format!("H02W{}01", &hm[3]), wx - 1, wy);
                    }
                } else if tx == max_x - 1 {
                    // H02E0000 --> x+1, H02E0001
                    // H02W0002 --> x+1, H02W00001
                    if &hm[2] == "E" && wx == max_x - 1 && &hm[4] == "00" {
                        return (format!("H02E{}01", &hm[3]), wx + 1, wy);
                    } else if &hm[2] == "W" && wx == max_x - 1 && &hm[4] == "02" {
                        return (format!("H02W{}01", &hm[3]), wx + 1, wy);
                    }
                }
            }
            "06" => {
                if tx <= 5 {
                    // x-2, H06W0302 --> x-3, H06W0303
                    // x-2, H06E0004 --> x-3, H06E0003
                    // x-1, H06W0301 --> x-3, H06W0303
                    // x-1, H06E0305 --> x-3, H06E0303
                    match &hm[2] {
                        "W" => {
                            return (
                                format!("H06W{}03", &hm[3]),
                                wx - (3 - hm[4].parse::<i32>().unwrap()),
                                wy,
                            )
                        }
                        "E" => {
                            return (
                                format!("H06E{}03", &hm[3]),
                                wx - (hm[4].parse::<i32>().unwrap() - 3),
                                wy,
                            )
                        }
                        _ => panic!("unknown H06 wire {}", wn),
                    }
                } else if tx >= max_x - 5 {
                    match &hm[2] {
                        "W" => {
                            return (
                                format!("H06W{}03", &hm[3]),
                                wx + (hm[4].parse::<i32>().unwrap() - 3),
                                wy,
                            )
                        }
                        "E" => {
                            return (
                                format!("H06E{}03", &hm[3]),
                                wx + (3 - hm[4].parse::<i32>().unwrap()),
                                wy,
                            )
                        }
                        _ => panic!("unknown H06 wire {}", wn),
                    }
                }
            }
            _ => panic!("bad HWIRE {}", &wn),
        }
    }
    if let Some(vm) = V_WIRE_RE.captures(wn) {
        match &vm[1] {
            "01" => {
                if ty == 1 {
                    if wy == 1 && &vm[2] == "N" && &vm[4] == "00" {
                        return (format!("V01{}{}01", &vm[2], &vm[3]), wx, wy - 1);
                    }
                    if wy == 1 && &vm[2] == "S" && &vm[4] == "01" {
                        return (format!("V01{}{}01", &vm[2], &vm[3]), wx, wy - 1);
                    }
                }
            }
            "02" => {
                if ty == 1 {
                    if &vm[2] == "S" && wy == 1 && &vm[4] == "02" {
                        return (format!("V02S{}01", &vm[3]), wx, wy - 1);
                    }
                    if &vm[2] == "N" && wy == 1 && &vm[4] == "00" {
                        return (format!("V02N{}01", &vm[3]), wx, wy - 1);
                    }
                } else if ty == max_y - 1 {
                    if &vm[2] == "S" && wy == (max_y - 1) && &vm[4] == "00" {
                        return (format!("V02S{}01", &vm[3]), wx, wy + 1);
                    }
                    if &vm[2] == "N" && wy == (max_y - 1) && &vm[4] == "02" {
                        return (format!("V02N{}01", &vm[3]), wx, wy + 1);
                    }
                }
            }
            "06" => {
                if ty <= 5 {
                    // y-2, V06N0302 --> y-3, H06W0303
                    // y-2, V06S0004 --> y-3, V06S0003
                    // y-1, V06N0301 --> y-3, V06N0303
                    // y-1, V06S0005 --> y-3, V06S0003
                    match &vm[2] {
                        "N" => {
                            return (
                                format!("V06N{}03", &vm[3]),
                                wx,
                                wy - (3 - vm[4].parse::<i32>().unwrap()),
                            )
                        }
                        "S" => {
                            return (
                                format!("V06S{}03", &vm[3]),
                                wx,
                                wy - (vm[4].parse::<i32>().unwrap() - 3),
                            )
                        }
                        _ => panic!("unknown V06 wire {}", wn),
                    }
                } else if ty >= max_y - 5 {
                    // y+2, V06N0304 --> y+3, V06N0303
                    // y+2, V06S0302 --> x+3, V06S0303
                    match &vm[2] {
                        "N" => {
                            return (
                                format!("V06N{}03", &vm[3]),
                                wx,
                                wy + (vm[4].parse::<i32>().unwrap() - 3),
                            )
                        }
                        "S" => {
                            return (
                                format!("V06S{}03", &vm[3]),
                                wx,
                                wy + (3 - vm[4].parse::<i32>().unwrap()),
                            )
                        }
                        _ => panic!("unknown V06 wire {}", wn),
                    }
                }
            }
            _ => panic!("bad VWIRE {}", &wn),
        }
    }
    (wn.to_string(), wx, wy)
}

pub fn normalize_wire(chip: &Chip, tile: &Tile, wire: &str) -> String {
    /*
    Wire name normalisation for tile wires and fuzzing
    All net names that we have access too are canonical, global names
    These are thus no good for building up a database that is the same for all tiles
    of a given type, as the names will be different in each location.

    Lattice names are of the form R{r}C{c}_{WIRENAME}

    Hence, we normalise names in the following way:
     - Global wires have the prefix "G:" added
     - Wires where (r, c) correspond to the current tile have their prefix removed
     - Wires to the left (in TAPs) are given the prefix BRANCH_L:, and wires to the right
       are given the prefix BRANCH_R:
     - Wires corresponding to the global network branch, spine or HROWs are given
       BRANCH:, SPINE:, or HROW: prefixes accordingly
     - Wires within a DQS group are given the prefix DQSG:
     - Other wires are given a relative position prefix using the syntax
       ([NS]\d+)?([EW]\d+)?:
       so a wire whose nominal location is 6 tiles up would be given a prefix N6:
       a wire whose nominal location is 2 tiles down and 1 tile right would be given a prefix
       S2E1:

    N.B. the ':' symbol is not legal in some contexts such as FASM. In these cases it is to be replaced by a
    '__' token.

    This is more complicated at the edges of the device, where irregular names are used to keep the row and column
    of the nominal position in bounds. Extra logic is be needed to catch and regularise these cases.

    Returns the normalised netname
    */
    let spw = WIRE_RE
        .captures(wire)
        .expect(&format!("invalid wire name '{}'", wire));
    let (mut wy, mut wx, mut wn) = (
        spw[1].parse::<i32>().unwrap(),
        spw[2].parse::<i32>().unwrap(),
        &spw[3],
    );
    if wn.ends_with("VCCHPRX") || wn.ends_with("VCCHPBX") || wn.ends_with("VCC")
        // LIFCL-33 has VCCSPINEs which connect to VCCHPRX
        || wn.ends_with("VCCVSPINE") {
        return "G:VCC".to_string();
    }
    let tx = tile.x as i32;
    let ty = tile.y as i32;

    if tile.name.contains("TAP") && (wn.starts_with("HPRX") || wn.starts_with("HPBX")) && !wn.starts_with("HFIE") {
        let branch_dir = match chip.device.as_str() {
            "LIFCL-40" | "LIFCL-17" | "LFD2NX-40" | "LFCPNX-100" =>
                if wx < tx {
                    Some("L")
                } else if wx > tx {
                    Some("R")
                } else {
                    None
                }

            // On every device except the 33's, the column the tap is on is the first column of the R side.
            // Probably the real fix is to pass the globals database in and have it sort it with that data.
            "LIFCL-33U" | "LIFCL-33" => {
                let first_r_col = match tx {
                    // Column tap is on -> First column of the R side of the tap
                    14 => 14,
                    26 => 38,
                    _ => panic!("Invalid tap column given: {} {}", wx, tx)
                };
                if wx >= first_r_col {
                    Some("R")
                } else {
                    Some("L")
                }
            }
            _ => None,
        }.expect(format!("unable to determine TAP side of {} in {}", wire, tile.name).as_str());

        return format!("BRANCH_{}:{}", branch_dir, wn);
    }

    if GLB_HBRANCH_RE.is_match(wn) {
        return format!("BRANCH:{}", wn);
    } else if GLB_SPINE_RE.is_match(wn) {
        return format!("SPINE:{}", wn);
    } else if GLB_HROW_RE.is_match(wn) {
        return format!("HROW:{}", wn);
    } else if is_full_global_wn(wn) {
        return format!("G:{}", wn);
    } else if DQS_GROUP_RE.is_match(wn) {
        return format!("DQSG:{:}", wn);
    } else if BANK_VREF_RE.is_match(wn) {
        return format!("BANK:{:}", wn);
    }
    let en = handle_edge_name(
        chip.data.max_col as i32,
        chip.data.max_row as i32,
        tx,
        ty,
        wx,
        wy,
        wn,
    );
    wn = &en.0;
    wx = en.1;
    wy = en.2;
    if wx == tx && wy == ty {
        return wn.to_string();
    } else {
        let mut prefix = String::new();
        if wy < ty {
            prefix.push_str(&format!("N{}", ty - wy));
        }
        if wy > ty {
            prefix.push_str(&format!("S{}", wy - ty));
        }
        if wx > tx {
            prefix.push_str(&format!("E{}", wx - tx));
        }
        if wx < tx {
            prefix.push_str(&format!("W{}", tx - wx));
        }
        return format!("{}:{}", prefix, wn);
    }
}

pub fn is_site_wire(tiletype: &str, wire: &str) -> bool {
    // Return true if a wire is part of a site; false if part of tile routing
    match tiletype {
        "PLC" => {
            wire.contains("_SLICE") || wire.ends_with("_DIMUX") || wire.ends_with("_DRMUX") || wire.ends_with("_CDMUX")
        },
        _ => false,
    }
}
