use crate::bba::bbafile::*;
use crate::bba::idstring::*;
use crate::bels::*;

use std::convert::TryInto;
use std::io::Result;

pub struct BBAStructs<'a> {
    pub out: &'a mut BBAWriter<'a>,
}

// *MUST* update this here and in nextpnr whenever making changes
pub const BBA_VERSION: u32 = 4;

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
        self.out.ref_label(ports_ref)?; // ref to list of ports
        self.out.u32_val(num_ports.try_into().unwrap())?; // number of ports
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
        self.out.u32_val(num_uh.try_into().unwrap())?; // number of uphill pips
        self.out.u32_val(num_dh.try_into().unwrap())?; // number of downhill pips
        self.out.u32_val(num_bp.try_into().unwrap())?; // number of bel pins
        self.out.ref_label(pips_uh_ref)?; // ref to list of uphill pips
        self.out.ref_label(pips_dh_ref)?; // ref to list of downhill pips
        self.out.ref_label(bel_pins_ref)?; // ref to list of bel pins
        Ok(())
    }

    pub fn tile_pip(
        &mut self,
        from_wire: usize,
        to_wire: usize,
        flags: u16,
        tile_type: IdString,
    ) -> Result<()> {
        self.out.u16_val(from_wire.try_into().unwrap())?; // src wire index in tile
        self.out.u16_val(to_wire.try_into().unwrap())?; // dst wire index in tile
        self.out.u16_val(flags)?; // pip flags
        self.out.u16_val(0)?; // padding (reserved for timing class)
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
        self.out.u32_val(num_neighbours.try_into().unwrap())?; // number of wire neighbours
        self.out.ref_label(nwire_ref)?; // ref to list of wire neighbours
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

    pub fn idstring_list(&mut self, label: &str, strings: &[String]) -> Result<()> {
        self.out.label(label)?;
        for id in strings {
            self.out.str_val(&id)?;
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
        self.out.u32_val(num_bels.try_into().unwrap())?;
        self.out.u32_val(num_wires.try_into().unwrap())?;
        self.out.u32_val(num_pips.try_into().unwrap())?;
        self.out.u32_val(num_nhtypes.try_into().unwrap())?;
        self.out.ref_label(bels_ref)?;
        self.out.ref_label(wires_ref)?;
        self.out.ref_label(pips_ref)?;
        self.out.ref_label(nh_ref)?;
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
        self.out.u16_val(num_phys_tiles.try_into().unwrap())?;
        self.out.ref_label(phys_tiles_ref)?;
        Ok(())
    }

    pub fn spine_col_list(&mut self, label: &str, spine_cols: &[usize]) -> Result<()> {
        self.out.label(label)?;
        for &x in spine_cols {
            self.out.u16_val(x.try_into().unwrap())?;
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
        self.out.u32_val(num_spine_cols.try_into().unwrap())?;
        self.out.ref_label(spine_cols_ref)?;
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
        self.out.u32_val(num_branches.try_into().unwrap())?;
        self.out.u32_val(num_spines.try_into().unwrap())?;
        self.out.u32_val(num_hrows.try_into().unwrap())?;
        self.out.ref_label(branches_ref)?;
        self.out.ref_label(spines_ref)?;
        self.out.ref_label(hrows_ref)?;
        Ok(())
    }

    pub fn id_string_db(
        &mut self,
        num_file_ids: usize,
        num_bba_ids: usize,
        bba_ids_ref: &str,
    ) -> Result<()> {
        self.out.u32_val(num_file_ids.try_into().unwrap())?;
        self.out.u32_val(num_bba_ids.try_into().unwrap())?;
        self.out.ref_label(bba_ids_ref)?;
        Ok(())
    }

    pub fn device(
        &mut self,
        device_name: &str,
        width: usize,
        height: usize,
        num_tiles: usize,
        grid_ref: &str,
        globals_ref: &str,
    ) -> Result<()> {
        self.out.str_val(device_name)?;
        self.out.u16_val(width.try_into().unwrap())?;
        self.out.u16_val(height.try_into().unwrap())?;
        self.out.u32_val(num_tiles.try_into().unwrap())?;
        self.out.ref_label(grid_ref)?;
        self.out.ref_label(globals_ref)?;
        Ok(())
    }

    pub fn database(
        &mut self,
        num_chips: usize,
        family: &str,
        chips_ref: &str,
        num_loctypes: usize,
        loctypes_ref: &str,
    ) -> Result<()> {
        self.out.u32_val(BBA_VERSION)?;
        self.out.u32_val(num_chips.try_into().unwrap())?;
        self.out.u32_val(num_loctypes.try_into().unwrap())?;
        self.out.str_val(family)?;
        self.out.ref_label(chips_ref)?;
        self.out.ref_label(loctypes_ref)?;
        self.out.ref_label("id_db")?;
        Ok(())
    }
}
