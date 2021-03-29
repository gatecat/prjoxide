#![cfg(feature = "interchange")]

use crate::bba::idxset::IndexedMap;
use crate::sites::*;
use crate::interchange_gen::routing_graph::*;
use crate::interchange_gen::bel_pin_map::get_pin_maps;

use crate::schema::*;
use crate::chip::Chip;
use crate::database::Database;
use crate::bba::idstring::*;
use crate::bels::PinDir;

use std::convert::TryInto;

use flate2::Compression;
use flate2::write::GzEncoder;

pub fn write(c: &Chip, _db: &mut Database, ids: &mut IdStringDB, graph: &IcGraph, filename: &str) -> ::capnp::Result<()> {
    let mut m = ::capnp::message::Builder::new_default();
    {
        let mut dev = m.init_root::<DeviceResources_capnp::device::Builder>();
        let mut uniq_site_types = IndexedMap::<String, Site>::new();
        dev.set_name(&c.device);
        {
            let mut tiletypes = dev.reborrow().init_tile_type_list(graph.tile_types.len().try_into().unwrap());
            for (i, (_, data)) in graph.tile_types.iter().enumerate() {
                let mut tt = tiletypes.reborrow().get(i.try_into().unwrap());
                // TODO: form a nice name from the constituent tile types
                // TODO: remove the NULL hack
                if i == graph.tiles[0].type_idx {
                    tt.set_name(ids.id("NULL").val().try_into().unwrap());
                } else {
                    tt.set_name(ids.id(&format!("tiletype_{}", i)).val().try_into().unwrap());
                }
                {
                    let mut sites = tt.reborrow().init_site_types(data.site_types.len().try_into().unwrap());
                    for (j, site_type) in data.site_types.iter().enumerate() {
                        // TODO: shared site types across multiple tile types?
                        let type_idx = uniq_site_types.add(&site_type.site_type, site_type.clone());
                        let mut site = sites.reborrow().get(j.try_into().unwrap());
                        site.set_primary_type(type_idx.try_into().unwrap());
                        {
                            let mut pins = site.init_primary_pins_to_tile_wires(site_type.pins.len().try_into().unwrap());
                            for (k, site_pin) in site_type.pins.iter().enumerate() {
                                pins.set(k.try_into().unwrap(), ids.id(&site_pin.tile_wire).val().try_into().unwrap());
                            }
                        }
                    }
                }
                {
                    let mut wires = tt.reborrow().init_wires(data.wires.len().try_into().unwrap());
                    for (j, (_, wire_data)) in data.wires.iter().enumerate() {
                        wires.set(j.try_into().unwrap(),  wire_data.name.val().try_into().unwrap());
                    }
                }
                {
                    let mut pips = tt.reborrow().init_pips(data.pips.len().try_into().unwrap());
                    for (j, pip_data) in data.pips.iter().enumerate() {
                        let mut p = pips.reborrow().get(j.try_into().unwrap());
                        p.set_wire0(pip_data.src_wire.try_into().unwrap());
                        p.set_wire1(pip_data.dst_wire.try_into().unwrap());
                        p.set_directional(true);
                        p.set_buffered20(true);
                        p.set_buffered21(false);
                        p.set_conventional(());
                    }
                }
                // TODO: constant sources
            }
        }
        {
            // Site types
            let mut sitetypes = dev.reborrow().init_site_type_list(uniq_site_types.len().try_into().unwrap());
            for (i, (_, data)) in uniq_site_types.iter().enumerate() {
                let mut st = sitetypes.reborrow().get(i.try_into().unwrap());
                st.set_name(ids.id(&data.site_type).val().try_into().unwrap());
                st.set_last_input(data.last_input_pin.try_into().unwrap());
                {
                    let mut bels = st.reborrow().init_bels(data.bels.len().try_into().unwrap());
                    for (j, bel_data) in data.bels.iter().enumerate() {
                        let mut bel = bels.reborrow().get(j.try_into().unwrap());
                        bel.set_name(ids.id(&bel_data.name).val().try_into().unwrap());
                        bel.set_type(ids.id(&bel_data.bel_type).val().try_into().unwrap());
                        bel.set_category(match bel_data.bel_class {
                            SiteBelClass::BEL => DeviceResources_capnp::device::BELCategory::Logic,
                            SiteBelClass::RBEL => DeviceResources_capnp::device::BELCategory::Routing,
                            SiteBelClass::PORT => DeviceResources_capnp::device::BELCategory::SitePort,
                        });
                        bel.set_non_inverting(());
                        {
                            let mut bel_pins = bel.reborrow().init_pins(bel_data.pins.len().try_into().unwrap());
                            for (k, pin) in bel_data.pins.iter().enumerate() {
                                bel_pins.set(k.try_into().unwrap(), (*pin).try_into().unwrap());
                            }
                        }
                    }
                }
                {
                    let mut bel_pins = st.reborrow().init_bel_pins(data.bel_pins.len().try_into().unwrap());
                    for (j, pin_data) in data.bel_pins.iter().enumerate() {
                        let mut bp = bel_pins.reborrow().get(j.try_into().unwrap());
                        bp.set_name(ids.id(&pin_data.pin_name).val().try_into().unwrap());
                        bp.set_dir(match pin_data.dir {
                            PinDir::INPUT => LogicalNetlist_capnp::netlist::Direction::Input,
                            PinDir::OUTPUT => LogicalNetlist_capnp::netlist::Direction::Output,
                            PinDir::INOUT => LogicalNetlist_capnp::netlist::Direction::Inout,
                        });
                        bp.set_bel(ids.id(&pin_data.bel_name).val().try_into().unwrap());
                    }
                }
                {
                    let mut wires = st.reborrow().init_site_wires(data.wires.len().try_into().unwrap());
                    for (j, wire_data) in data.wires.iter().enumerate() {
                        let mut w = wires.reborrow().get(j.try_into().unwrap());
                        w.set_name(ids.id(&wire_data.name).val().try_into().unwrap());
                        {
                            let mut bel_pins = w.reborrow().init_pins(wire_data.bel_pins.len().try_into().unwrap());
                            for (k, pin) in wire_data.bel_pins.iter().enumerate() {
                                bel_pins.set(k.try_into().unwrap(), (*pin).try_into().unwrap());
                            }
                        }
                    }
                }
                {
                    let mut pips = st.reborrow().init_site_p_i_ps(data.pips.len().try_into().unwrap());
                    for (j, pip_data) in data.pips.iter().enumerate() {
                        let mut p = pips.reborrow().get(j.try_into().unwrap());
                        p.set_inpin(pip_data.in_pin.try_into().unwrap());
                        p.set_outpin(pip_data.out_pin.try_into().unwrap());
                    }
                }
                {
                    let mut pins = st.reborrow().init_pins(data.pins.len().try_into().unwrap());
                    for (j, pin_data) in data.pins.iter().enumerate() {
                        let mut p = pins.reborrow().get(j.try_into().unwrap());
                        p.set_name(ids.id(&pin_data.site_wire).val().try_into().unwrap());
                        p.set_dir(match pin_data.dir {
                            PinDir::INPUT => LogicalNetlist_capnp::netlist::Direction::Input,
                            PinDir::OUTPUT => LogicalNetlist_capnp::netlist::Direction::Output,
                            PinDir::INOUT => LogicalNetlist_capnp::netlist::Direction::Inout,
                        });
                        p.set_belpin(pin_data.bel_pin.try_into().unwrap());
                    }
                }
            }
        }
        let mut wire_list = Vec::new();
        {
            // this wire_list is the list of wires as we create nodes, to be output as dev.wires later
            let mut nodes = dev.reborrow().init_nodes(graph.nodes.len().try_into().unwrap());
            for (i, node_data) in graph.nodes.iter().enumerate() {
                let n = nodes.reborrow().get(i.try_into().unwrap());
                let mut node_wires = n.init_wires(node_data.wires.len().try_into().unwrap());
                // write root wire
                {
                    node_wires.set(0, wire_list.len().try_into().unwrap());
                    wire_list.push((node_data.root_wire.tile_name, node_data.root_wire.wire_name));
                }
                let mut node_wire_idx = 1;
                // write non-root wires
                for wire in node_data.wires.iter().filter(|w| **w != node_data.root_wire) {
                    node_wires.set(node_wire_idx, wire_list.len().try_into().unwrap());
                    wire_list.push((wire.tile_name, wire.wire_name));
                    node_wire_idx += 1;
                }
            }
        }
        {
            let mut wires = dev.reborrow().init_wires(wire_list.len().try_into().unwrap());
            for (i, (tile_name, wire_name)) in wire_list.iter().enumerate() {
                let mut w = wires.reborrow().get(i.try_into().unwrap());
                w.set_tile(tile_name.val().try_into().unwrap());
                w.set_wire(wire_name.val().try_into().unwrap());
            }
        }
        {
            let mut tiles = dev.reborrow().init_tile_list(graph.tiles.len().try_into().unwrap());
            for (i, tile_data) in graph.tiles.iter().enumerate() {
                let mut t = tiles.reborrow().get(i.try_into().unwrap());
                t.set_name(tile_data.name.val().try_into().unwrap());
                t.set_type(tile_data.type_idx.try_into().unwrap());
                t.set_row(tile_data.y.try_into().unwrap());
                t.set_col(tile_data.x.try_into().unwrap());
                {
                    let tt = graph.tile_types.value(tile_data.type_idx);
                    let mut sites = t.reborrow().init_sites(tt.site_types.len().try_into().unwrap());
                    for (j, site_data) in tt.site_types.iter().enumerate() {
                        let mut s = sites.reborrow().get(j.try_into().unwrap());
                        s.set_name(ids.id(&format!("R{}C{}_{}", tile_data.y, tile_data.x, &site_data.name)).val().try_into().unwrap());
                        s.set_type(j.try_into().unwrap());
                    }
                }
            }
        }
        {
            let mut constants = dev.reborrow().init_constants();
            constants.set_gnd_cell_type(ids.id("VLO").val().try_into().unwrap());
            constants.set_gnd_cell_pin(ids.id("Z").val().try_into().unwrap());
            constants.set_vcc_cell_type(ids.id("VHI").val().try_into().unwrap());
            constants.set_vcc_cell_pin(ids.id("Z").val().try_into().unwrap());
        }
        {
            let mut constraints = dev.reborrow().init_constraints();
            {
                let mut cc = constraints.reborrow().init_cell_constraints(1);
                {
                    let mut lut_constr = cc.reborrow().get(0);
                    lut_constr.set_cell("LUT4");
                    let mut lut_loc = lut_constr.init_locations(1).get(0);
                    lut_loc.reborrow().init_site_types(1).set(0, "PLC");
                    {
                        let mut lut_bels = lut_loc.reborrow().init_bel().init_bels(8);
                        for i in 0..8 {
                            lut_bels.set(i,
                                &format!("SLICE{}_LUT{}", "ABCD".chars().nth((i / 2) as usize).unwrap(), i % 2));
                        }
                    }
                    lut_loc.reborrow().init_implies(0);
                }
            }
        }
        {
            let mut pin_maps = Vec::new();
            for (site_type, site) in uniq_site_types.iter() {
                pin_maps.extend(get_pin_maps(site).drain(..).map(|x| (site_type.to_string(), x)));
            }
            let mut c2b = dev.reborrow().init_cell_bel_map((2 + pin_maps.len()).try_into().unwrap());
            c2b.reborrow().get(0).set_cell(ids.id("VLO").val().try_into().unwrap());
            c2b.reborrow().get(1).set_cell(ids.id("VHI").val().try_into().unwrap());
            for (i, (site_type, pin_map_data)) in pin_maps.iter().enumerate() {
                let mut m = c2b.reborrow().get((2 + i).try_into().unwrap());
                m.set_cell(ids.id(&pin_map_data.cell_type).val().try_into().unwrap());
                let mut pin_map = m.init_common_pins(1).get(0);
                {
                    let mut st = pin_map.reborrow().init_site_types(1).get(0);
                    st.set_site_type(ids.id(&site_type).val().try_into().unwrap());
                    let mut bels = st.init_bels(pin_map_data.bels.len().try_into().unwrap());
                    for (j, bel) in pin_map_data.bels.iter().enumerate() {
                        bels.set(j.try_into().unwrap(), ids.id(&bel).val().try_into().unwrap());
                    }
                }
                {
                    let mut pins = pin_map.init_pins(pin_map_data.pin_map.len().try_into().unwrap());
                    for (j, (cell_pin, bel_pin)) in pin_map_data.pin_map.iter().enumerate() {
                        pins.reborrow().get(j.try_into().unwrap()).set_cell_pin(ids.id(cell_pin).val().try_into().unwrap());
                        pins.reborrow().get(j.try_into().unwrap()).set_bel_pin(ids.id(bel_pin).val().try_into().unwrap());
                    }
                }
            }

        }
        {
            let mut packages = dev.reborrow().init_packages(1);
            packages.reborrow().get(0).set_name(ids.id("QFN72").val().try_into().unwrap());
            // TODO: all packages and pin map
        }
        {
            let mut strs = dev.init_str_list(ids.len().try_into().unwrap());
            for i in 0..ids.len() {
                strs.set(i.try_into().unwrap(), ids.idx_str(i));
            }
        }
    }
    let mut e = GzEncoder::new(std::fs::File::create(filename)?, Compression::default());
    ::capnp::serialize::write_message(&mut e, &m)?;
    e.finish()?;
    Ok(())
}
