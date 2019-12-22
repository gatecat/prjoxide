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
    static ref GLB_HROWD_RE: Regex = Regex::new(r"^([LR])HPRX(\d+)$").unwrap();
    // Central clock signals
    static ref GLB_CMUXI_RE: Regex = Regex::new(r"^J([HV])F([NESW])(\d+)_(DCSMUX|CMUX)_CORE_(DCSMUX|CMUX)(\d)$").unwrap();
    // Perimeter clock signals
    static ref GLB_MIDMUX_RE: Regex = Regex::new(r"^(.*)(.)MID_CORE_(.)MIDMUX$").unwrap();
    // Edge clock signals
    static ref ECLK_RE: Regex = Regex::new(r"^JECLKOUT(\d)_ECLKCASMUX_CORE_ECLKCASMUX(\d+)$").unwrap();
    // Edge clock sources
    static ref ECLK_MUXIN_RE: Regex = Regex::new(r"^JMUXIN(\d+)_ECLKBANK_CORE_ECLKBANK(\d+)$").unwrap();
    // DQS group shared signals
    static ref DQS_GROUP_RE: Regex = Regex::new(r"^J(WRPNTR\d|RDPNTR\d|DQSR90|DQSW270|DQSW)_DQSBUF_CORE_I_DQS_TOP$").unwrap();
}

fn is_full_global_wn(wire: &str) -> bool {
    GLB_HROWD_RE.is_match(wire)
        || GLB_CMUXI_RE.is_match(wire)
        || GLB_MIDMUX_RE.is_match(wire)
        || ECLK_RE.is_match(wire)
        || ECLK_MUXIN_RE.is_match(wire)
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
    let (wy, wx, wn) = (
        spw[1].parse::<u32>().unwrap(),
        spw[2].parse::<u32>().unwrap(),
        &spw[3],
    );
    if tile.name.contains("TAP") && wn.starts_with("H") {
        if wx < tile.x {
            return format!("BRANCH_L:{}", wn);
        } else if wx > tile.x {
            return format!("BRANCH_R:{}", wn);
        } else {
            panic!("unable to determine TAP side of {} in {}", wire, tile.name);
        }
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
    }
    if wx == tile.x && wy == tile.y {
        return wn.to_string();
    } else {
        let mut prefix = String::new();
        if wy < tile.y {
            prefix.push_str(&format!("N{}", tile.y - wy));
        }
        if wy > tile.y {
            prefix.push_str(&format!("S{}", wy - tile.y));
        }
        if wx > tile.x {
            prefix.push_str(&format!("E{}", wx - tile.x));
        }
        if wx < tile.x {
            prefix.push_str(&format!("W{}", tile.x - wx));
        }
        return format!("{}:{}", prefix, wn);
    }
}
