import asyncio
import logging
import re
import sys
import traceback
from asyncio import CancelledError
from collections import defaultdict

import lapie

import cachecontrol
import fuzzconfig
import fuzzloops
import interconnect
import libpyprjoxide
import nonrouting
import primitives
import radiant
import tiles
from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect_sinks
from fuzzloops import wrap_future
import database

import libpyprjoxide

###
# This fuzzer pulls up each site, figures out its relationship to tiletypes, and then find the routeing and primitive
# mappings for those representative tile(s).
###

# These tiles overlap many sites and are not the main site tiles
overlapping_tile_types = set(["CIB", "MIB_B_TAP", "TAP_CIB"] +
                             [f"BANKREF{i}" for i in range(16)] +
                             [f"BK{i}_15K" for i in range(16)]
                             )

def get_site_tiles(device, site):
    site_tiles = [tile for tile in tiles.get_tiles_by_rc(device, site) if
                  tile.split(":")[1] not in overlapping_tile_types]

    return site_tiles

semaphore = asyncio.Semaphore(16)

# Pull from a bitstream baseline delta the main tile and IP changes
def find_relevant_tiles_from_bitstream(device, site, active_bitstream):
    deltas, ip_values = fuzzconfig.find_baseline_differences(device, active_bitstream)

    power_tile_types = set(["PMU"] + [f"BANKREF{i}" for i in range(16)])
    pmu_tiles = [x for x in list(deltas.keys()) if x.split(":")[-1] in power_tile_types]

    delta_sorted = [x[0] for x in sorted(deltas.items(), key=lambda x: -len(x[1]))]
    driving_tiles = [x for x in delta_sorted if x.split(":")[-1] not in power_tile_types]
    site_tiles = [tile for tile in tiles.get_tiles_by_rc(device, site) if
                  tile.split(":")[1] not in overlapping_tile_types]

    # This happens for DCC, DCS
    if len(site_tiles) == 0:
        site_tiles = driving_tiles

    return (driving_tiles + pmu_tiles), site_tiles, ip_values

# Look at the site pins and map out the nodes on those pins. Find the deltas that enable those pips.
async def find_relevant_tiles(device, site, site_type, site_info, executor):
    cfg = FuzzConfig(job=f"{site}:{site_type}", device=device, tiles=[])

    nodes = [p["pin_node"] for p in site_info["pins"]]
    logging.info(f"Getting relevant wire tiles for {device} {site}:{site_type}")
    pips, _ = tiles.get_local_pips_for_nodes(device, nodes, include_interface_pips=True,
                                       should_expand=lambda p: p[0] in nodes or p[1] in nodes)

    wires_bitstream = await asyncio.wrap_future(interconnect.create_wires_file(cfg, pips, prefix=f"find-relevant-tiles/", executor = executor))

    driving_tiles, site_tiles, ip_values = find_relevant_tiles_from_bitstream(device, site, wires_bitstream)

    return ([t for t in driving_tiles if t.split(":")[-1] != "PLC"],
            [t for t in site_tiles if t.split(":")[-1] != "PLC"],
            ip_values
            )

# If we have a primitive definition, use it to generate a bitstream and compare it to baseline. This delta shows which
# tiles the site belongs to.
async def find_relevant_tiles_from_primitive(device, primitive, site, site_info, executor):
    site_type = site_info["type"]

    cfg = FuzzConfig(job=f"{site}:{site_type}", device=device, tiles=[])

    primitive_bitstream = await asyncio.wrap_future(cfg.build_design_future(executor, "./primitive.v", {
        "config": primitive.fill_config(),
        "site": site,
        "site_type": site_type,
        "extra": "",
        "signals": ""
    }, prefix=f"find-relevant-tiles/mode-{primitive.mode}/"))
    logging.info(f"Getting relevant tiles for {device} {site}:{site_type} for {primitive.mode}")

    return find_relevant_tiles_from_bitstream(device, site, primitive_bitstream)

    # # Also get the tiling from just the wiring
    # pin_driving_tiles, pin_site_tiles, pin_ip_values = await find_relevant_tiles(device, site, site_type, site_info, executor = executor)
    #
    # # Note: We do this to keep ordering but removing dups
    # def uniq(x):
    #     return list(dict.fromkeys(x))
    #
    # return uniq(driving_tiles + pin_driving_tiles), uniq(site_tiles + pin_site_tiles), uniq(ip_values + pin_ip_values)

mux_re = re.compile("MUX[0-9]*$")

# Use the primitive definitions to map out each mode's options. Works for IP and non IP settings
async def map_primitive_settings(device, ts, site, site_tiles, site_info, ip_values, overlays, executor = None):
    site_type = site_info["type"]
    if site_type not in primitives.primitives:
        logging.warning(f"Site type {site_type} isn't mapped to a primitive")
        return []

    empty_file = FuzzConfig.standard_empty(device)

    base_addrs = database.get_base_addrs(device)

    if site not in base_addrs:
        ip_values = []

    is_ip_config = len(ip_values) > 0
    if len(ip_values):
        fuzz_enum_setting = nonrouting.fuzz_ip_enum_setting
        fuzz_word_setting = nonrouting.fuzz_ip_word_setting
    else:
        fuzz_enum_setting = nonrouting.fuzz_enum_setting
        fuzz_word_setting = nonrouting.fuzz_word_setting

    async def map_mode(mode):
        site_id = mode.belname(site, site_info, ts)
        needs_overlay = mode.needs_overlay
        logging.info(f"====== {device} {mode.mode} : {site_id}:{site_type} IP: {len(ip_values)} ==========")
        related_tiles = (ts + site_tiles)
        cfg = FuzzConfig(job=f"config/{site_type}/{ts[0].split(":")[-1]}/{site_id}/{mode.mode}", device=device, sv="primitive.v",
                         tiles= related_tiles if len(ip_values) == 0 else [f"{site}:{site_type}"])

        slice_sites = tiles.get_tiles_by_tiletype(device, "PLC")
        slice_iter = iter([x for x in slice_sites if tiles.get_rc_from_name(device, x) not in related_tiles])

        extra_lines = []
        signals = []

        avail_in_pins = []
        for p in mode.pins:
            if p.dir == "in" or p.dir == "inout":
                for r in range(0, p.bits if p.bits is not None else 1):
                    suffix = str(r) if p.bits != None else ""
                    avail_in_pins.append(f"{p.name}{suffix}")
        q_driver = None
        def get_sink_pin():
            if len(avail_in_pins):
                in_pin = avail_in_pins.pop()
                extra_lines.append(f"wire q_{in_pin};")
                signals.append(f".{in_pin}(q_{in_pin})")
                return f"q_{in_pin}"

            idx = len(extra_lines)
            extra_lines.append(f"""
            wire q_{idx};            
            (* \\dm:cellmodel_primitives ="REG0=reg", \\dm:primitive ="SLICE", \\dm:programming ="MODE:LOGIC Q0:Q0 ", \\dm:site ="{next(slice_iter).split(":")[0]}A" *) 
            SLICE SLICE_I_{idx} ( .A0(q_{idx}) );
                        """)
            return f"q_{idx}"

        for p in mode.pins:
            for r in range(0, p.bits if p.bits is not None else 1):
                suffix = str(r) if p.bits != None else ""
                if p.dir == "out":
                    q = get_sink_pin()
                    q_driver = q
                    signals.append(f".{p.name}{suffix}({q})")

        if len(avail_in_pins) and q_driver is None:
            extra_lines.append(f"""
                    wire q_driver;            
                    (* \\dm:cellmodel_primitives ="REG0=reg", \\dm:primitive ="SLICE", \\dm:programming ="MODE:LOGIC Q0:Q0 ", \\dm:site ="{next(slice_iter).split(":")[0]}A" *) 
                    SLICE SLICE_I_driver ( .A0(q_driver), .Q0(q_driver) );
                """)
            q_driver = "q_driver"

        for undriven_pin in avail_in_pins:
            signals.append(f".{undriven_pin}({q_driver})")

        if needs_overlay:
            overlays[f"{tiletype}-{device}"].append(ts[0])

        subs = {
            "site": site,
            "site_type": site_type,
            "extra": "\n".join(extra_lines),
            "signals": ", ".join(signals)
        }

        async def map_mode_setting(setting):
            mark_relative_to = None
            if len(site_tiles) > 0 and site_tiles[0] != ts[0]:
                mark_relative_to = site_tiles[0]

            args = {
                "config": cfg,
                "name": f"{site_id}.{setting.name}",# "name": f"{mode.mode}.{setting.name}",
                "desc": setting.desc,
                "executor": executor,
            }

            if needs_overlay:
                args["overlay"] = f"{device}"

            if isinstance(setting, primitives.EnumSetting):
                subs_fn = lambda val, setting=setting, mode=mode: subs | {"config": mode.configuration([(setting, val)])}

                # if len(ip_values) == 0:
                #     args["mark_relative_to"] = mark_relative_to

                if isinstance(setting, primitives.ProgrammablePin) and not is_ip_config:
                    args["include_zeros"] = True

                await wrap_future(fuzz_enum_setting(empty_bitfile = empty_file, values = setting.values, get_sv_substs = subs_fn, **args))
            elif isinstance(setting, primitives.WordSetting):
                def subs_fn(val):
                    return subs | {"config": mode.configuration([(setting, nonrouting.fuzz_intval(val))])}

                await wrap_future(fuzz_word_setting(length=setting.bits, get_sv_substs=subs_fn, **args))
            else:
                raise Exception(f"Unknown setting type: {setting}")

        await asyncio.gather(*[map_mode_setting(s) for s in mode.settings])

    primitive = primitives.primitives[site_type]
    with fuzzconfig.db_lock() as db:
        site_rc = tiles.get_rc_from_name(device, site)
        tiletype = ts[0].split(":")[-1]
        site_tile_rc = tiles.get_rc_from_name(db, ts[0])
        if site_rc is None:
            site_rc = site_tile_rc

        node_datas = {v.name:v for v in lapie.get_node_data(device, [pin["pin_node"] for pin in site_info["pins"]])}

        for idx, primitive_mode in enumerate(primitive):
            if primitive_mode.beltype is None:
                continue
            site_id = primitive_mode.belname(site, site_info, ts)
            def clean_name(name):
                if name.startswith("CIB"): return name[3:]
                return name
            def create_wire(pin_node):
                name, (rr, rc) = tiles.resolve_relative_node(device, pin_node, site_rc)
                return {
                    "rel_x": rc,
                    "rel_y": rr,
                    "name": name
                }
            def node_dir(pin_node):
                node_info = node_datas[pin_node]
                if len(node_info.uphill_pips) > 0 and len(node_info.downhill_pips) > 0:
                    return "INOUT"
                elif len(node_info.uphill_pips) > 0:
                    return "INPUT"
                return "OUTPUT"

            overlay_name = tiletype
            if primitive_mode.needs_overlay:
                overlay_name = f"overlays/{tiletype}-{device}"

            db.add_bel(database.get_family_for_device(device), overlay_name, {
                "name": site_id,
                "beltype": primitive_mode.beltype,
                "pins": sorted([
                    {
                        "name": clean_name(pin["pin_name"]),
                        "dir": node_dir(pin["pin_node"]),
                        "wire": create_wire(pin["pin_node"])
                    } for pin in site_info["pins"]
                ], key=lambda pin: pin["name"]),
                "rel_x": site_rc[1] - site_tile_rc[1],
                "rel_y": site_rc[0] - site_tile_rc[0],
                "z": 0
            })
        db.flush()

    return await asyncio.gather(*[map_mode(mode) for mode in primitive])

site_type_warnings = set()
async def run_for_device(device, executor = None):
    overlays = defaultdict(list)

    if not fuzzconfig.should_fuzz_platform(device):
        return

    async def find_relevant_tiles_for_site(site, site_info, executor):
        if should_skip_site(site, site_info):
            return None

        site_type = site_info["type"]

        if site_type in primitives.primitives:
            primitive = primitives.primitives[site_type][0]

            return await find_relevant_tiles_from_primitive(device, primitive, site, site_info, executor=executor)

        if site_type not in site_type_warnings:
            logging.warning(f"No primitives defined for {site}:{site_type}")
            site_type_warnings.add(site_type)
        return [], [], []

    def should_skip_site(site, site_info):
        site_type = site_info["type"]
        if len(sys.argv) > 1 and sys.argv[1] != site_type:
            return True

        if site_type in ["PLL_CORE"] and device in ["LIFCL-33U"]:
            logging.warning(f"Can't map out IP core {site_type} with device {device} which is in readback mode")
            return True

        if site_type in ["CIBTEST", "SLICE"]:
            return True

        return False

    async def per_site(site, site_info, driving_tiles, overlays, executor):
        (driving_tiles, site_tiles, ip_values) = driving_tiles

        tiletype = driving_tiles[0].split(":")[1]
        logging.info(f"====== {site} : {tiletype} {driving_tiles} {site_info["type"]} ==========")

        # Map primitive parameter settings
        await map_primitive_settings(device, driving_tiles + site_tiles, site, site_tiles, site_info, ip_values, overlays, executor = executor)

    sites = database.get_sites(device)
    sites_items = [(k, v) for k, v in sorted(sites.items()) if v["type"] not in ["CIBTEST", "SLICE"]]

    driving_tiles_futures = []
    for site, site_info in sites_items:
        driving_tiles_futures.append(find_relevant_tiles_for_site(site, site_info, executor=executor))

    all_driving_tiles = await asyncio.gather(*driving_tiles_futures)
    mapped_sites = set()

    try:
        async with (asyncio.TaskGroup() as tg):
            for (site, site_info), driving_tiles_rtn in zip(sites_items, all_driving_tiles):
                if driving_tiles_rtn is None:
                    continue

                driving_tiles, site_tiles, ip_values = driving_tiles_rtn

                driving_tiles = [t for t in driving_tiles if t.split(":")[1] not in ["PLC", "TAB_CIB", "CIB"]]

                if len(driving_tiles) == 0:
                    if site_info["type"] not in site_type_warnings:
                        site_type_warnings.add(site_info["type"])
                        logging.warning(f"Could not find driving tiles for {site}:{site_info["type"]}")
                    continue

                logging.debug(f"Driving sites for {site}:")
                for t in set(driving_tiles + site_tiles):
                    logging.debug(f"   - {t}")

                # Certain sites present different even with the same site_type and tile_type surrounding it. Specifically
                # IO types have A and B suffixes. The IP and configuration is the same, but the pins map to differently
                # named wires and it is the wire name that matters for the DB. So we key on the wire names too
                site_key = (
                    site_info["type"],
                    tuple(sorted(t.split(":")[-1] for t in driving_tiles)),
                    tuple(sorted(f"{p["pin_name"]}:{"_".join(p["pin_node"].split("_")[1:])}" for p in site_info["pins"]))
                )

                logging.debug(f"Site key: {site_key}")
                if site_key in mapped_sites:
                    continue

                mapped_sites.add(site_key)
                tg.create_task(per_site(site, site_info, (driving_tiles, site_tiles, ip_values), overlays, executor))

        fuzzconfig.register_device_overlays(device, "116-site-mappings", overlays)
    except* CancelledError:
        pass
    except* BaseException as eg:
        logging.error(f"Caught an exception group for base: {eg} {eg.exceptions}")
        for e in eg.exceptions:
            traceback.print_exception(e)
        raise


async def FuzzAsync(executor):
    families = database.get_devices()["families"]
    devices = sorted([
        device
        for family in families
        for device in families[family]["devices"]
        if fuzzconfig.should_fuzz_platform(device)
    ])

    all_sites = set([site_info["type"]
                     for device in devices
                     if device.startswith("LIFCL")
                     for site, site_info in database.get_sites(device).items()
                     ])

    if len(sys.argv) > 1 and sys.argv[1] not in all_sites:
        logging.warning(f"Site filter doesn't match any known sites")
        logging.info(sorted(all_sites))
        return

    for device in devices:
        await asyncio.gather(*[ run_for_device(device, executor) ])

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(FuzzAsync)
