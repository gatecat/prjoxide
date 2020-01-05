use crate::bba::bbafile::*;
use crate::bba::idstring::*;
use crate::bels::*;

use std::convert::TryInto;
use std::io::Result;

pub struct BBAStructs<'a> {
    out: &'a mut BBAWriter<'a>,
}

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
        ports_ref: &str,
        num_ports: usize,
    ) -> Result<()> {
        self.out.u32_val(name.val().try_into().unwrap())?; // bel name IdString
        self.out.u32_val(beltype.val().try_into().unwrap())?; // bel type IdString
        self.out.i16_val(rel_x)?; // actual location relative X
        self.out.i16_val(rel_y)?; // actual location relative Y
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
        pips_uh_ref: &str,
        pips_dh_ref: &str,
        bel_pins_ref: &str,
        num_uh: usize,
        num_dh: usize,
        num_bp: usize,
    ) -> Result<()> {
        self.out.u32_val(name.val().try_into().unwrap())?; // wire name IdString
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
        tile_type: IdString,
    ) -> Result<()> {
        self.out.u16_val(from_wire.try_into().unwrap())?; // src wire index in tile
        self.out.u16_val(to_wire.try_into().unwrap())?; // dst wire index in tile
        self.out.u32_val(tile_type.val().try_into().unwrap())?; // tile type containing pip IdString
        Ok(())
    }

    pub fn rel_wire(&mut self, flags: u16, rel_x: i16, rel_y: i16, wire_idx: usize) -> Result<()> {
        self.out.u16_val(flags)?; // for special cases like globals
        self.out.i16_val(rel_x)?; // neighbour loc X
        self.out.i16_val(rel_y)?; // neighbour loc Y
        self.out.u16_val(wire_idx.try_into().unwrap())?; // index of wire in neighbour tile
        Ok(())
    }
}
