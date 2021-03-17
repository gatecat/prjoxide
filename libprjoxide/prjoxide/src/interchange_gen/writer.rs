#![cfg(feature = "interchange")]

use crate::interchange_gen::routing_graph::*;
use crate::schema::*;
use crate::chip::Chip;
use crate::database::Database;
use crate::bba::idstring::*;

use std::convert::TryInto;

use flate2::Compression;
use flate2::write::GzEncoder;

pub fn write(c: &Chip, _db: &mut Database, ids: &mut IdStringDB, graph: &IcGraph, filename: &str) -> ::capnp::Result<()> {
    let mut m = ::capnp::message::Builder::new_default();
    {
        let mut dev = m.init_root::<DeviceResources_capnp::device::Builder>();
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
                    wire_list.push((node_data.root_wire.tile_idx, node_data.root_wire.wire_idx));
                }
                let mut node_wire_idx = 1;
                // write non-root wires
                for wire in node_data.wires.iter().filter(|w| **w != node_data.root_wire) {
                    node_wires.set(node_wire_idx, wire_list.len().try_into().unwrap());
                    wire_list.push((wire.tile_idx, wire.wire_idx));
                    node_wire_idx += 1;
                }
            }
        }
        {
            let mut wires = dev.reborrow().init_wires(wire_list.len().try_into().unwrap());
            for (i, (tile_idx, wire_idx)) in wire_list.iter().enumerate() {
                let mut w = wires.reborrow().get(i.try_into().unwrap());
                // TODO: should IcGraph use IdStrings to better match what we write out?
                let tile = &graph.tiles[*tile_idx];
                w.set_tile(tile.name.val().try_into().unwrap());
                w.set_wire(graph.tile_types.value(tile.type_idx).wires.value(*wire_idx).name.val().try_into().unwrap());
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
            let mut c2b = dev.reborrow().init_cell_bel_map(2);
            c2b.reborrow().get(0).set_cell(ids.id("VLO").val().try_into().unwrap());
            c2b.reborrow().get(1).set_cell(ids.id("VHI").val().try_into().unwrap());
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
