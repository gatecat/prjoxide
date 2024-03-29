use crate::bba::bbafile::*;
use crate::bba::idstring::*;
use crate::bels::*;

use std::convert::TryInto;
use std::io::Result;

pub struct BBAStructs<'a> {
    pub out: &'a mut BBAWriter<'a>,
}

// *MUST* update this here and in nextpnr whenever making changes
pub const BBA_VERSION: u32 = 11;

// Wire flags
pub const WIRE_PRIMARY: u32 = 0x80000000;
// Neighbour arc flags
pub const LOGICAL_TO_PRIMARY: u8 = 0x80;
pub const PHYSICAL_DOWNHILL: u8 = 0x08;
// Neighbour location flags
pub const REL_LOC_XY: u8 = 0;
pub const REL_LOC_GLOBAL: u8 = 1;
pub const REL_LOC_BRANCH: u8 = 2;
pub const REL_LOC_BRANCH_L: u8 = 3;
pub const REL_LOC_BRANCH_R: u8 = 4;
pub const REL_LOC_SPINE: u8 = 5;
pub const REL_LOC_HROW: u8 = 6;
pub const REL_LOC_VCC: u8 = 7;
// Tile location flags
pub const LOC_LOGIC: u32 = 0x000001;
pub const LOC_IO18: u32 = 0x000002;
pub const LOC_IO33: u32 = 0x000004;
pub const LOC_BRAM: u32 = 0x000008;
pub const LOC_DSP: u32 = 0x000010;
pub const LOC_IP: u32 = 0x000020;
pub const LOC_CIB: u32 = 0x000040;
pub const LOC_TAP: u32 = 0x001000;
pub const LOC_SPINE: u32 = 0x002000;
pub const LOC_TRUNK: u32 = 0x004000;
pub const LOC_MIDMUX: u32 = 0x008000;
pub const LOC_CMUX: u32 = 0x010000;
// Pip flags
pub const PIP_DRMUX_C : u16 = 0x1000;
pub const PIP_ZERO_RR_COST: u16 = 0x2000;
pub const PIP_LUT_PERM: u16 = 0x4000;
pub const PIP_FIXED_CONN: u16 = 0x8000;

impl<'a> BBAStructs<'a> {
    pub fn new(out: &'a mut BBAWriter<'a>) -> BBAStructs<'a> {
        BBAStructs { out }
    }

    pub fn bel_wire(&mut self, port: IdString, pintype: PinDir, wire_idx: usize) -> Result<()> {
        self.out.u32_val(port.val().try_into().unwrap())?; // port name IdString
        self.out.u16_val(pintype as u16)?; // port direction
        self.out.u16_val(wire_idx.try_into().unwrap())?; // index of port wire in tile
        Ok(())
    }

    pub fn bel_info(
        &mut self,
        name: IdString,
        beltype: IdString,
        rel_x: i16,
        rel_y: i16,
        z: u32,
        ports_ref: &str,
        num_ports: usize,
    ) -> Result<()> {
        self.out.u32_val(name.val().try_into().unwrap())?; // bel name IdString
        self.out.u32_val(beltype.val().try_into().unwrap())?; // bel type IdString
        self.out.i16_val(rel_x)?; // actual location relative X
        self.out.i16_val(rel_y)?; // actual location relative Y
        self.out.u32_val(z)?; // bel Z-coordinate
        self.out.ref_slice(ports_ref, num_ports)?; // ref to list of ports
        Ok(())
    }

    pub fn bel_pin(&mut self, bel_idx: usize, pin: IdString) -> Result<()> {
        self.out.u32_val(bel_idx.try_into().unwrap())?; // bel index in tile
        self.out.u32_val(pin.val().try_into().unwrap())?; // port name IdString
        Ok(())
    }

    pub fn pips_list(&mut self, label: &str, pip_ids: &[usize]) -> Result<()> {
        self.out.label(label)?;
        for &id in pip_ids {
            self.out.u32_val(id.try_into().unwrap())?;
        }
        Ok(())
    }

    pub fn tile_wire(
        &mut self,
        name: IdString,
        flags: u32,
        pips_uh_ref: &str,
        pips_dh_ref: &str,
        bel_pins_ref: &str,
        num_uh: usize,
        num_dh: usize,
        num_bp: usize,
    ) -> Result<()> {
        self.out.u32_val(name.val().try_into().unwrap())?; // wire name IdString
        self.out.u32_val(flags)?;
        self.out.ref_slice(pips_uh_ref, num_uh)?; // ref to list of uphill pips
        self.out.ref_slice(pips_dh_ref, num_dh)?; // ref to list of downhill pips
        self.out.ref_slice(bel_pins_ref, num_bp)?; // ref to list of bel pins
        Ok(())
    }

    pub fn tile_pip(
        &mut self,
        from_wire: usize,
        to_wire: usize,
        flags: u16,
        timing_class: usize,
        tile_type: IdString,
    ) -> Result<()> {
        self.out.u16_val(from_wire.try_into().unwrap())?; // src wire index in tile
        self.out.u16_val(to_wire.try_into().unwrap())?; // dst wire index in tile
        self.out.u16_val(flags)?; // pip flags
        self.out.u16_val(timing_class.try_into().unwrap())?; // timing class index
        self.out.u32_val(tile_type.val().try_into().unwrap())?; // tile type containing pip IdString
        Ok(())
    }

    pub fn rel_wire(
        &mut self,
        loc_type: u8,
        arc_flags: u8,
        rel_x: i16,
        rel_y: i16,
        wire_idx: usize,
    ) -> Result<()> {
        self.out.i16_val(rel_x)?; // neighbour loc X
        self.out.i16_val(rel_y)?; // neighbour loc Y
        self.out.u16_val(wire_idx.try_into().unwrap())?; // index of wire in neighbour tile
        self.out.u8_val(loc_type)?; // for special cases like globals
        self.out.u8_val(arc_flags)?; // direction info
        Ok(())
    }

    pub fn wire_neighbours(&mut self, nwire_ref: &str, num_neighbours: usize) -> Result<()> {
        self.out.ref_slice(nwire_ref, num_neighbours)?; // ref to list of wire neighbours
        Ok(())
    }

    pub fn list_begin(&mut self, name: &str) -> Result<()> {
        self.out.label(name)?;
        Ok(())
    }

    pub fn reference(&mut self, ref_label: &str) -> Result<()> {
        self.out.ref_label(ref_label)?;
        Ok(())
    }

    pub fn ref_slice(&mut self, ref_label: &str, len: usize) -> Result<()> {
        self.out.ref_slice(ref_label, len)?;
        Ok(())
    }

    pub fn string_list(&mut self, label: &str, strings: &[String]) -> Result<()> {
        self.out.label(label)?;
        for id in strings {
            self.out.str_val(&id)?;
        }
        Ok(())
    }

    pub fn id_list(&mut self, label: &str, ids: &[u32]) -> Result<()> {
        self.out.label(label)?;
        for id in ids {
            self.out.u32_val(*id)?;
        }
        Ok(())
    }

    pub fn loc_type(
        &mut self,
        num_bels: usize,
        num_wires: usize,
        num_pips: usize,
        num_nhtypes: usize,
        bels_ref: &str,
        wires_ref: &str,
        pips_ref: &str,
        nh_ref: &str,
    ) -> Result<()> {
        self.out.ref_slice(bels_ref, num_bels)?;
        self.out.ref_slice(wires_ref, num_wires)?;
        self.out.ref_slice(pips_ref, num_pips)?;
        self.out.ref_slice(nh_ref, num_nhtypes)?;
        Ok(())
    }

    pub fn physical_tile(&mut self, prefix: IdString, tiletype: IdString) -> Result<()> {
        self.out.u32_val(prefix.val().try_into().unwrap())?;
        self.out.u32_val(tiletype.val().try_into().unwrap())?;
        Ok(())
    }

    pub fn grid_loc(
        &mut self,
        loc_type: usize,
        loc_flags: u32,
        nh_type: usize,
        num_phys_tiles: usize,
        phys_tiles_ref: &str,
    ) -> Result<()> {
        self.out.u32_val(loc_type.try_into().unwrap())?;
        self.out.u32_val(loc_flags)?;
        self.out.u16_val(nh_type.try_into().unwrap())?;
        self.out.u16_val(0)?; // padding
        self.out.ref_slice(phys_tiles_ref, num_phys_tiles)?;
        Ok(())
    }

    pub fn spine_col_list(&mut self, label: &str, spine_cols: &[usize]) -> Result<()> {
        self.out.label(label)?;
        for &x in spine_cols {
            self.out.u32_val(x.try_into().unwrap())?;
        }
        Ok(())
    }

    pub fn global_branch_info(
        &mut self,
        branch_col: usize,
        from_col: usize,
        tap_driver_col: usize,
        tap_side: &str,
        to_col: usize,
    ) -> Result<()> {
        self.out.u16_val(branch_col.try_into().unwrap())?;
        self.out.u16_val(from_col.try_into().unwrap())?;
        self.out.u16_val(tap_driver_col.try_into().unwrap())?;
        self.out.u16_val(
            (tap_side.chars().next().unwrap() as u32)
                .try_into()
                .unwrap(),
        )?;
        self.out.u16_val(to_col.try_into().unwrap())?;
        self.out.u16_val(0)?; // padding
        Ok(())
    }

    pub fn global_spine_info(
        &mut self,
        from_row: usize,
        to_row: usize,
        spine_row: usize,
    ) -> Result<()> {
        self.out.u16_val(from_row.try_into().unwrap())?;
        self.out.u16_val(to_row.try_into().unwrap())?;
        self.out.u16_val(spine_row.try_into().unwrap())?;
        self.out.u16_val(0)?; // padding
        Ok(())
    }

    pub fn global_hrow_info(
        &mut self,
        hrow_col: usize,
        num_spine_cols: usize,
        spine_cols_ref: &str,
    ) -> Result<()> {
        self.out.u16_val(hrow_col.try_into().unwrap())?;
        self.out.u16_val(0)?; // padding
        self.out.ref_slice(spine_cols_ref, num_spine_cols)?;
        Ok(())
    }

    pub fn package_info(
        &mut self,
        full_name: &str,
        short_name: &str
    ) -> Result<()> {
        self.out.str_val(full_name)?;
        self.out.str_val(short_name)?;
        Ok(())
    }

    pub fn pad_info(
        &mut self,
        offset: i32,
        side: i8,
        pio_index: i32,
        bank: i32,
        dqs_group: i32,
        dqs_func: i32,
        vref_index: i32,
        num_funcs: usize,
        num_pins: usize,
        func_str_ref: &str,
        pins_ref: &str,
    ) -> Result<()> {
        self.out.i16_val(offset.try_into().unwrap())?;
        self.out.i8_val(side)?;
        self.out.i8_val(pio_index.try_into().unwrap())?;
        self.out.i16_val(bank.try_into().unwrap())?;
        self.out.i16_val(dqs_group.try_into().unwrap())?;
        self.out.i8_val(dqs_func.try_into().unwrap())?;
        self.out.i8_val(vref_index.try_into().unwrap())?;
        self.out.u16_val(0)?; // padding
        self.out.ref_slice(func_str_ref, num_funcs)?;
        self.out.ref_slice(pins_ref, num_pins)?;
        Ok(())
    }

    pub fn global_info(
        &mut self,
        num_branches: usize,
        num_spines: usize,
        num_hrows: usize,
        branches_ref: &str,
        spines_ref: &str,
        hrows_ref: &str,
    ) -> Result<()> {
        self.out.ref_slice(branches_ref, num_branches)?;
        self.out.ref_slice(spines_ref, num_spines)?;
        self.out.ref_slice(hrows_ref, num_hrows)?;
        Ok(())
    }

    pub fn cell_prop_delay(
        &mut self,
        from_port: IdString,
        to_port: IdString,
        min_delay: i32,
        max_delay: i32,
    ) -> Result<()> {
        self.out.u32_val(from_port.val().try_into().unwrap())?; // from port IdString
        self.out.u32_val(to_port.val().try_into().unwrap())?; // from port IdString
        self.out.i32_val(min_delay)?; // min delay in ps
        self.out.i32_val(max_delay)?; // max delay in ps
        Ok(())
    }

    pub fn cell_setup_hold(
        &mut self,
        sig_port: IdString,
        clock_port: IdString,
        min_setup: i32,
        max_setup: i32,
        min_hold: i32,
        max_hold: i32,
    ) -> Result<()> {
        self.out.u32_val(sig_port.val().try_into().unwrap())?; // from port IdString
        self.out.u32_val(clock_port.val().try_into().unwrap())?; // clock port IdString
        self.out.i32_val(min_setup)?; // min setup time in ps
        self.out.i32_val(max_setup)?; // max setup time in ps
        self.out.i32_val(min_hold)?; // min hold time in ps
        self.out.i32_val(max_hold)?; // max hold time in ps
        Ok(())
    }

    pub fn cell_timing(
        &mut self,
        cell_type: IdString,
        cell_variant: IdString,
        num_prop_delays: usize,
        num_setup_holds: usize,
        prop_delays_ref: &str, // must be sorted by (from, to)
        setup_holds_ref: &str, // must be sorted by (sig, clk)
    ) -> Result<()> {
        self.out.u32_val(cell_type.val().try_into().unwrap())?;
        self.out.u32_val(cell_variant.val().try_into().unwrap())?;
        self.out.ref_slice(prop_delays_ref, num_prop_delays)?;
        self.out.ref_slice(setup_holds_ref, num_setup_holds)?;
        Ok(())
    }

    pub fn pip_timing(
        &mut self,
        min_delay: i32,
        max_delay: i32,
        min_fanout_adder: i32,
        max_fanout_adder: i32,
    ) -> Result<()> {
        self.out.i32_val(min_delay)?;
        self.out.i32_val(max_delay)?;
        self.out.i32_val(min_fanout_adder)?;
        self.out.i32_val(max_fanout_adder)?;
        Ok(())
    }

    pub fn speed_grade(
        &mut self,
        name: &str,
        num_cell_types: usize,
        num_pip_classes: usize,
        cell_types_ref: &str,
        pip_classes_ref: &str,
    ) -> Result<()> {
        self.out.str_val(name)?;
        self.out.ref_slice(cell_types_ref, num_cell_types)?;
        self.out.ref_slice(pip_classes_ref, num_pip_classes)?;
        Ok(())
    }

    pub fn id_string_db(
        &mut self,
        num_file_ids: usize,
        num_bba_ids: usize,
        bba_ids_ref: &str,
    ) -> Result<()> {
        self.out.u32_val(num_file_ids.try_into().unwrap())?;
        self.out.ref_slice(bba_ids_ref, num_bba_ids)?;
        Ok(())
    }

    pub fn device(
        &mut self,
        device_name: &str,
        width: usize,
        height: usize,
        num_tiles: usize,
        num_pads: usize,
        num_pkgs: usize,
        grid_ref: &str,
        globals_ref: &str,
        pads_ref: &str,
        pkgs_ref: &str,
    ) -> Result<()> {
        self.out.str_val(device_name)?;
        self.out.u16_val(width.try_into().unwrap())?;
        self.out.u16_val(height.try_into().unwrap())?;
        self.out.ref_slice(grid_ref, num_tiles)?;
        self.out.ref_label(globals_ref)?;
        self.out.ref_slice(pads_ref, num_pads)?;
        self.out.ref_slice(pkgs_ref, num_pkgs)?;
        Ok(())
    }

    pub fn database(
        &mut self,
        num_chips: usize,
        family: &str,
        chips_ref: &str,
        num_loctypes: usize,
        num_speedgrades: usize,
        loctypes_ref: &str,
    ) -> Result<()> {
        self.out.u32_val(BBA_VERSION)?;
        self.out.str_val(family)?;
        self.out.ref_slice(chips_ref, num_chips)?;
        self.out.ref_slice(loctypes_ref, num_loctypes)?;
        self.out.ref_slice("speed_grades", num_speedgrades)?;
        self.out.ref_label("id_db")?;
        Ok(())
    }
}
