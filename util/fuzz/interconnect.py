"""
Utilities for fuzzing interconect
"""
import asyncio
import logging
import os
import random
import re
from collections import defaultdict
from functools import cache
from logging.handlers import RotatingFileHandler

import cachecontrol
import lapie
import libpyprjoxide
import tiles

import database
import fuzzconfig
import fuzzloops
from DesignFileBuilder import get_wires_delta, DesignsForPips, BitConflictException, create_wires_file

def make_dict_of_lists(lst, key = None):
    if key is None:
        key = lambda x: x[0]

    rtn = defaultdict(list)
    for item in lst:
        rtn[key(item)].append(item)
    return rtn

def setup_size_rotating_log(log_file):
    logger = logging.getLogger("SizeRotatingLog")

    # Rotate when file reaches 1MB (1024*1024 bytes), keep 5 backups
    logger.addHandler(RotatingFileHandler(
        log_file,
        maxBytes=1024 * 1024 * 64,
        backupCount=1
    ))
    logger.propagate = False
    logger.setLevel("INFO")
    return logger

transaction_log = setup_size_rotating_log(database.get_db_root() + "/db_transaction.log")

def pips_to_sinks(pips):
    sinks = {}

    for from_wire, to_wire in pips:
        if to_wire not in sinks:
            sinks[to_wire] = []
        sinks[to_wire].append(from_wire)

    for k in sinks:
        sinks[k] = sorted(sinks[k])

    return sinks

def collect_sinks(config, nodenames, regex = False,
                 nodename_predicate=lambda x, nets: True,
                 pip_predicate=lambda x, nets: True,
                 bidir=False,
                 nodename_filter_union=False,
                 ):
    if regex:
        all_nodes = lapie.get_full_node_list(config.device)
        regex = [re.compile(n) for n in nodenames]
        nodenames = [n for n in all_nodes if any([r for r in regex if r.search(n) is not None])]
        regex = False

    nodes = lapie.get_node_data(config.device, nodenames, regex)

    all_wirenames = set([n.name for n in nodes])
    all_pips = set()
    for node in nodes:
        for p in node.uphill_pips:
            all_pips.add((p.from_wire, p.to_wire))
        if bidir:
            for p in node.downhill_pips:
                all_pips.add((p.from_wire, p.to_wire))
    per_sink = list(sorted(all_pips))
    
    # First filter using netname predicate
    if nodename_filter_union:
        all_pips = filter(lambda x: nodename_predicate(x[0], all_wirenames) and nodename_predicate(x[1], all_wirenames),
                            all_pips)
    else:
        all_pips = filter(lambda x: nodename_predicate(x[0], all_wirenames) or nodename_predicate(x[1], all_wirenames),
                            all_pips)
    # Then filter using the pip predicate
    fuzz_pips = list(filter(lambda x: pip_predicate(x, all_wirenames), all_pips))
    if len(fuzz_pips) == 0:
        logging.warning(f"No fuzz_pips defined for job {config}. Nodes: {nodes} {all_pips}")
        return {}

    return pips_to_sinks(fuzz_pips)

def fuzz_interconnect_sinks(
        config,
        sinks,
        full_mux_style=False,
        ignore_tiles=set(),
        extra_substs={},
        fc_filter=lambda x: True,
        executor = None
    ):
    if sinks is None:
        return []


    if not isinstance(sinks, dict):
        sinks = pips_to_sinks(sinks)

    assert(len(config.tiles) > 0)

    def process_bits(bitstreams, from_wires, to_wire):
        base_bitf = bitstreams[0]
        bitstreams = [b.bitstream if b is not None else None for b in bitstreams[1:]]

        with fuzzconfig.db_lock() as db:
            fz = libpyprjoxide.Fuzzer.pip_fuzzer(db, base_bitf.bitstream, set(config.tiles), to_wire,
                                                 config.tiles[0],
                                                 set(ignore_tiles), full_mux_style, not (fc_filter(to_wire)))

            pip_samples = [(from_wire, arc_bit if arc_bit is not None else base_bitf.bitstream) for (from_wire, arc_bit) in zip(from_wires, bitstreams)]
            fz.add_pip_samples(db, pip_samples)

            logging.debug(f"Solving for {to_wire}")
            config.solve(fz, db)

    conns = tiles.get_connections_for_device(config.device)

    connection_pips = []
    for to_wire in sinks:
        connection_pips.extend([(frm, to_wire) for frm in sinks[to_wire] if (frm, to_wire) in connection_pips])
        sinks[to_wire] = [frm for frm in sinks[to_wire] if (frm, to_wire) not in connection_pips]
        if len(sinks[to_wire]) == 0:
            sinks.pop(to_wire)

    logging.info(f"Processing {len(sinks)} sinks for {sum([len(v) for k,v in sinks.items()])} designs for {config.job} {config.device}")

    with fuzzloops.Executor(executor) as executor:
        futures = []

        base_bitf_future = config.build_design_future(executor, config.sv, extra_substs, "base_")

        for to_wire in sinks:
            if config.check_deltas(to_wire):
                continue

            bitstream_futures = [base_bitf_future]
            for from_wire in sinks[to_wire]:
                arcs_attr = r', \dm:arcs ="{}.{}"'.format(to_wire, from_wire)
                substs = extra_substs.copy()
                substs["arcs_attr"] = arcs_attr

                arc_bit = None
                if to_wire in conns.get(from_wire, {}):
                    logging.debug(f"{from_wire} -> {to_wire} is in arc list; not building file")
                else:
                    logging.debug(f"Building design for ({config.job} {config.device}) {to_wire} to {from_wire}")
                    arc_bit = config.build_design_future(executor, config.sv, substs, f"{from_wire}/{to_wire}/")
                    futures.append(arc_bit)

                bitstream_futures.append(arc_bit)

            futures.append(fuzzloops.chain(bitstream_futures, "Interconnect sink", process_bits, sinks[to_wire], to_wire))

        futures.append(executor.submit(register_tile_connections, config.device, config.tiles[0].split(":")[-1], config.tiles[0], connection_pips))

        return futures

def fuzz_interconnect(
        config,
        nodenames,
        regex=False,
        nodename_predicate=lambda x, nets: True,
        pip_predicate=lambda x, nets: True,
        bidir=False,
        nodename_filter_union=False,
        full_mux_style=False,
        ignore_tiles=set(),
        extra_substs={},
        fc_filter=lambda x: True,
        executor = None
    ):
    """
    Fuzz interconnect given a list of nodenames to analyse. Pips associated these nodenames will be found using the Tcl
    API and bits identified as described above.

    :param config: FuzzConfig instance containing target device and tile(s) of interest
    :param nodenames: A list of nodes or node regexes in Lattice (un-normalised) format to analyse
    :param regex: enable regex names
    :param nodename_predicate: a predicate function which should return True if a netname is of interest, given
    the netname and the set of all nets
    :param pip_predicate: a predicate function which should return True if an arc, given the arc as a (source, sink)
    tuple and the set of all nodenames, is of interest
    :param bidir: if True, pips driven by as well as driving the given nodenames will be considered during analysis
    :param nodename_filter_union: if True, pips will be included if either net passes nodename_predicate, if False both
    nets much pass the predicate.
    :param full_mux_style: if True, is a full mux, and all 0s is considered a valid config bit possibility
    on certain families.
    :param ignore_tiles: don't reject pips that touch these tils
	:param extra_substs: extra SV substitutions
    :param fc_filter: skip fixed connections if this returns false for a sink wire name
    """
    if not fuzzconfig.should_fuzz_platform(config.device):
        return []

    sinks = collect_sinks(config, nodenames, regex = regex,
                          nodename_predicate = nodename_predicate,
                          pip_predicate = pip_predicate,
                          bidir=bidir,
                          nodename_filter_union=False)

    return fuzz_interconnect_sinks(config, sinks, full_mux_style, ignore_tiles, extra_substs, fc_filter, executor=executor)

def fuzz_interconnect_for_tiletype(device, tiletype):
    prototype = list(tiles.get_tiles_by_tiletype(device, tiletype).keys())[0]

    nodes = tiles.get_connected_nodes(device, prototype)
    
    connected_tiles = tiles.get_connected_tiles(device, prototype)

    cfg = fuzzconfig.FuzzConfig(job=f"interconnect_{tiletype}", device=device, tiles=[prototype])
    #fuzz_interconnect(config=cfg, nodenames=nodes, bidir=True)
    return collect_sinks(cfg, nodes, bidir=True)

def fuzz_interconnect_pins(config, site_name, extra_substs = {}, full_mux_style = False, fc_filter=lambda x: True):    
    pins = tiles.get_pins_for_site(config.device, site_name)

    family = config.device.split("-")[0]
    suffix = config.device.split("-")[1]    
    empty_sv = database.get_db_root() + f"/../fuzzers/{family}/shared/empty_{suffix}.v"
    base_bitf = config.build_design(empty_sv, extra_substs, "base_")
    
    def per_pip(pin_info, pin_pip):
        # Get a unique prefix from the thread ID

        print(pin_info, pin_pip)
        pin_name = pin_info['pin_name']
        to_wire = pin_pip.to_wire
        from_wire = pin_pip.from_wire
        is_output = pin_info['pin_node'] == pin_pip.from_wire
    
        prefix = "{}_{}_{}_".format(config.job, config.device, to_wire)

        with fuzzconfig.db_lock() as db:
            fz = libpyprjoxide.Fuzzer.pip_fuzzer(db, base_bitf.bitstream,
                                                 set(config.tiles),
                                                 to_wire,
                                                 config.tiles[0], set(), full_mux_style, not (fc_filter(to_wire)))

            arcs_attr = r', \dm:arcs ="{}.{}"'.format(to_wire, from_wire)
            substs = extra_substs.copy()
            substs["pin_name"] = pin_name
            substs["target"] = ".A0(q)" if is_output else ".Q0(q),.A0(q)"
            substs["arcs_attr"] = arcs_attr

            print(f"Building design for ({config.job} {config.device}) {to_wire} to {from_wire}")
            arc_bit = config.build_design(config.sv, substs, prefix)
            fz.add_pip_sample(db, from_wire, arc_bit.bitstream)

        config.solve(fz, db)

    for p, pnode in pins:
        assert(len(pnode.pips()) == 1)        
        per_pip(p, pnode.pips()[0])

# Cache this so we only do it once. Could also probably read the ron file and check it.
@cachecontrol.cache_fn()
def register_tile_connections(device, tiletype, tile, conn_pips):
    with fuzzconfig.db_lock() as db:
        db = libpyprjoxide.Database(database.get_db_root())
        family = device.split("-")[0]

        chip = libpyprjoxide.Chip(db, device)

        normalized_connections = [(chip.normalize_wire(tile, p[0]), chip.normalize_wire(tile, p[1])) for p in
                                  set(conn_pips)]
        db.add_conns(family, tiletype, normalized_connections)
        db.flush()

async def fuzz_interconnect_across_span(
        config,
        tile_span,
        nodenames,
        regex=False,
        nodename_predicate=lambda x, nets: True,
        pip_predicate=lambda x, nets: True,
        bidir=False,
        nodename_filter_union=False,
        full_mux_style=False,
        max_per_design = None,
        exclusion_list = [],
        executor = None):

    sinks = collect_sinks(config, nodenames, regex = regex,
                          nodename_predicate = nodename_predicate,
                          pip_predicate = pip_predicate,
                          bidir=bidir,
                          nodename_filter_union=nodename_filter_union)

    pips = [(frm, to) for to, froms in sinks.items() for frm in froms]

    await fuzz_interconnect_sinks_across_span(
        config, tile_span, pips,
        max_per_design=max_per_design,
        full_mux_style=full_mux_style,
        exclusion_list=exclusion_list,
        executor=executor
    )

def generate_mux_deltas(device_tiles, to_wire, from_wire_deltas, remove_constants = False):
    if isinstance(device_tiles, str):
        device_tiles = tiles.TilesHelper(device_tiles)

    device = device_tiles.device
    chip = device_tiles.chip()

    if len(from_wire_deltas) == 1 and len(list(from_wire_deltas.values())[0][1]) == 0:
        from_wire = list(from_wire_deltas.keys())[0]
        tile = rel_tile = list(from_wire_deltas.values())[0][0]
        nfrom_wire = tiles.resolve_actual_node(device, from_wire, rel_tile)
        nto_wire = tiles.resolve_actual_node(device, to_wire, rel_tile)

        norm_from_wire, norm_to_wire = chip.normalize_wire(rel_tile.split(",")[0], nfrom_wire), \
            chip.normalize_wire(rel_tile.split(",")[0], nto_wire)

        logging.debug(f"Adding mux pip {tile} {nfrom_wire} -> {nto_wire} empty_set")
        transaction_log.info(
            f"add_pip {device} {tile}: {nfrom_wire} -> {nto_wire} {norm_from_wire} -> {norm_to_wire} Bits: empty set")

        yield tile, nfrom_wire, nto_wire, set()

        return

    consistent_delta = None
    base_delta = None
    for (from_wire, (rel_tile, delta)) in from_wire_deltas.items():
        from_deltas = {
            (device_tiles.make_tile_anon(tile, rel_tile), frame_diff)
            for tile, frame_diffs in delta.items()
            for frame_diff in frame_diffs
        }
        if consistent_delta is None:
            consistent_delta = from_deltas
            base_delta = from_deltas
        else:
            consistent_delta = consistent_delta & from_deltas
            base_delta = base_delta | from_deltas

    if not remove_constants:
        consistent_delta = set()

    logging.debug(f"Generate mux base {base_delta} consistent {consistent_delta}")
    base_delta = base_delta - consistent_delta

    if len(from_wire_deltas) == 0:
        from_wire, (rel_tile, delta) = next(from_wire_deltas.items())

        nfrom_wire = tiles.resolve_actual_node(device, from_wire, rel_tile)
        nto_wire = tiles.resolve_actual_node(device, to_wire, rel_tile)

        yield rel_tile, nfrom_wire, nto_wire, set()


    for (from_wire, (rel_tile, delta)) in from_wire_deltas.items():
        from_deltas = {
                          (device_tiles.make_tile_anon(tile, rel_tile), frame_diff)
                          for (tile, frame_diffs) in delta.items()
                          for frame_diff in frame_diffs
                      } - consistent_delta

        coverage_delta = from_deltas & base_delta
        inverted_delta = {(tile, (f, b, not s)) for (tile, (f, b, s)) in (base_delta - from_deltas)}
        new_deltas = defaultdict(list)

        for (tile, delta) in (coverage_delta | inverted_delta):
            new_deltas[tile].append(delta)

        for (tile, delta) in new_deltas.items():
            nfrom_wire = tiles.resolve_actual_node(device, from_wire, rel_tile)
            nto_wire = tiles.resolve_actual_node(device, to_wire, rel_tile)

            norm_from_wire, norm_to_wire = chip.normalize_wire(rel_tile.split(",")[0], nfrom_wire), \
                chip.normalize_wire(rel_tile.split(",")[0], nto_wire)

            logging.debug(f"Adding mux pip {tile} {nfrom_wire} -> {nto_wire} {delta}")
            transaction_log.info(
                f"add_pip {device} {tile}: {nfrom_wire} -> {nto_wire} {norm_from_wire} -> {norm_to_wire} Bits: {delta}")
            concrete_tile = next(iter(device_tiles.resolve_anon_tile(tile, rel_tile)), None)

            yield concrete_tile, nfrom_wire, nto_wire, set(delta)

async def fuzz_interconnect_sinks_across_span(
        config,
        tile_span,
        pips,
        full_mux_style=False,
        max_per_design=None,
        exclusion_list=[],
        executor=None,
        overlay = None,
        check_pip_placement = True,
        builder = None
):

    nodes = set([w for p in pips for w in p])

    nodeinfos = {n.name:n for n in lapie.get_node_data(config.device, nodes)}
    if builder is not None: builder.reserve(1)

    device = config.device
    device_tiles = tiles.TilesHelper(device)

    @cache
    def get_node_info(x):
        if x in nodeinfos:
            return nodeinfos[x]
        else:
            db_node_info = lapie.get_node_data(config.device, x, skip_missing = True)
            # Entry appears normally in database
            if len(db_node_info) > 0 and db_node_info[0] is not None:
                return db_node_info[0]

            # Entry doesn't match as an existing node from the full node list
            if len(db_node_info) == 0:
                return None

            if x.split("_")[-1][0] in "VH":
                # Precache
                logging.info(f"Get info {x}")
                lapie.get_node_data(config.device, x.split("_")[0] + "_[VH].*", True)

            db_node_info = lapie.get_node_data(config.device, x)
            if len(db_node_info) > 0:
                return db_node_info[0]
            logging.warning("No node info found for {}".format(x))
            return None

    def make_anon_node(rc, p):
        return tiles.resolve_relative_node(device, p, rc)

    def fix_name(w):
        (wire_type, rc, *args) = tiles.resolve_relative_node(device, w)

        if wire_type in "NEWS":
            names = list(tiles.resolve_possible_names(device, w))
            #logging.info(f"Names {names} {w} {rc}")
            return names[(len(names) - 1)  //2]

        return w

    local_rng = random.Random(os.environ.get("OXIDE_RANDOM_SEED", 42))
    representative_tile = local_rng.choice(config.tiles)

    tiletype_or_overlay = representative_tile.split(":")[-1] if overlay is None else overlay
    representative_tile_rc = rc = (r, c) = tiles.get_rc_from_name(device, representative_tile)

    is_anon_pips = not isinstance(next(iter(pips))[0], str)

    def make_tile_anon(tile, rel_to):
        return device_tiles.make_tile_anon(tile, rel_to)

    def make_anon_pip(rc, p):
        return tuple([make_anon_node(rc, w) for w in p])

    if is_anon_pips:
        anon_pips = sorted(set([tuple([w for w in p]) for p in pips]))
        pips = [tuple(tiles.resolve_actual_node(device, n, (r, c)) for n in pip) for pip in anon_pips]
    else:
        anon_pips = sorted(set([make_anon_pip(rc, p) for p in pips]))

    modified_tiles_rcs_anon = []
    for tt, tt_tiles in sorted(make_dict_of_lists(config.tiles, lambda t: t.split(":")[-1]).items()):
        exemplar_tile = local_rng.choice(sorted(tt_tiles))
        exemplar_tile_rc = tiles.get_rc_from_name(device, exemplar_tile)
        exemplar_pips = [tuple(tiles.resolve_actual_node(device, n, exemplar_tile_rc) for n in pip) for pip in anon_pips]
        sinks = {k:list(v) for k,v in sorted(make_dict_of_lists(exemplar_pips, lambda p: p[1]).items())}
        exemplar_designs = []
        while len(sinks):
            design_pips = []
            for to_wire, pips_for_to in sorted(sinks.items()):
                design_pips.append(pips_for_to.pop())
            exemplar_designs.append(design_pips)
            sinks = {k: v for k, v in sinks.items() if len(v) > 0}

        exemplar_bitstream_infos = []
        filtered_deltas = defaultdict(list)

        for f in asyncio.as_completed([
            asyncio.wrap_future(
                get_wires_delta(config.device, exemplar_design, prefix=f"{exemplar_tile}/{tiletype_or_overlay}/{idx+1}_of_{len(exemplar_designs)}",executor=executor,with_bitstream_info=True,job_name=f"build-eval-design {device}")
            )
            for idx, exemplar_design in enumerate(exemplar_designs)
        ]):
            design_deltas, _, exemplar_bitstream_info = await f

            exemplar_bitstream_infos.append(exemplar_bitstream_info)
            for k,v in design_deltas.items():
                filtered_deltas[k].extend(v)

        modified_tiles_rcs_anon.extend([make_tile_anon(tile, exemplar_tile_rc) for tile in filtered_deltas.keys()])

    # PIPs are often controlled by nearby tiles. Convert those to relative positioned tiles. Since sometimes two tiles
    # will share an RC, we grab the tiletype too.

    connected_arcs = lapie.get_jump_wires_by_nodes(config.device, nodes)

    pips = set(pips) - set(connected_arcs)

    connected_arcs = [p for p in connected_arcs
                      if any([tiles.get_rc_from_name(device, w) == rc for w in p])]

    for arc in connected_arcs:
        transaction_log.info(f"add_conn {device} {tiletype_or_overlay}: {representative_tile} -> {arc}")

    register_tile_connections(config.device, tiletype_or_overlay, representative_tile, sorted(connected_arcs))

    chip = fuzzconfig.FuzzConfig.standard_chip(device)

    tile_suffix = "" if overlay is None else ",overlays/" + overlay

    if len(modified_tiles_rcs_anon) == 0:
        if len(pips) > 0:
            for (from_wire, to_wire) in pips:
                nfrom_wire = fix_name(from_wire)
                nto_wire = fix_name(to_wire)

                with fuzzconfig.db_lock() as db:
                    logging.debug(f"Adding conn {representative_tile} {nfrom_wire} -> {nto_wire} for empty set")
                    transaction_log.info(f"Adding conn {representative_tile} {nfrom_wire} -> {nto_wire} for empty set")
                    db.add_denormalized_conn(chip, representative_tile + tile_suffix, nfrom_wire, nto_wire)
        else:
            logging.warning(f"No modified tiles for {representative_tile} running no designs for interconnect.")

        if builder is not None: builder.unreserve(1)
        return

    if any(map(lambda x: callable(x) or x[1] != (0, 0), modified_tiles_rcs_anon)):
        logging.info(f"Modified tiles {modified_tiles_rcs_anon} {anon_pips[:5]}")

    rcs_for_tiles_of_tiletype = sorted([(tile, tiles.get_rc_from_name(device, tile)) for tile in tile_span])

    design_sets = []

    orig_anon_pips = [p for p in anon_pips]

    # Shuffle based on RNG seed. If several seeds do not demonstrate a bit conflict it indicates less chance of bugs
    shuffled_rcs_for_tiles_of_tiletype = [x for x in rcs_for_tiles_of_tiletype]
    local_rng.shuffle(shuffled_rcs_for_tiles_of_tiletype)

    design_sets = [d async for d in DesignsForPips(device_tiles,
                                     anon_pips,
                                     shuffled_rcs_for_tiles_of_tiletype,
                                     modified_tiles_rcs_anon)]

    logging.info(f"Found {len(orig_anon_pips)} standard pips total; results in {len(design_sets)} designs over {len(rcs_for_tiles_of_tiletype)} tiles with {representative_tile} ({tiletype_or_overlay}) as prototype")
    solve_tiletype_or_overlay = tiletype_or_overlay

    mux_deltas = defaultdict(dict)
    empty_deltas = dict()
    anon_pip_delta_tiles = defaultdict(list)

    async def process_design(idx, design_set):
        design_set_no_nulls = {k:v for k,v in design_set.items() if v is not None}
        pips = [tuple(pip_rcs[0]) for tile, pip_rcs in design_set_no_nulls.items()]
        assert(len(pips) == len(set(pips)))

        prefix = f"{solve_tiletype_or_overlay}/{idx+1}_of_{len(design_sets)}_{len(design_set_no_nulls)}_pips/"

        if builder is None:
            deltas, _, bitstream = await asyncio.wrap_future(get_wires_delta(config.device, pips, prefix=prefix, executor=executor, with_bitstream_info=True, job_name=f'build-compare-design {device}'))
        else:
            deltas, bitstream = await builder.build_design({k:v[0] if v is not None else None for k,v in design_set.items()})

        # We should never have deltas appearing where design_set doesnt have entries
        unexpected_deltas = set(deltas.keys()) - set(design_set.keys())
        if (len(unexpected_deltas) > 0):
            logging.error(f"Got unexpected deltas from {bitstream.vfiles}: Deltas: {unexpected_deltas}. Design: {design_set} Exemplar: {[i.vfiles for i in exemplar_bitstream_infos]} {filtered_deltas} modified_tiles {modified_tiles_rcs_anon}")
        assert(len(unexpected_deltas) == 0)

        rc_deltas = defaultdict(list)
        for k, v in deltas.items():
            rc_deltas[tiles.get_rc_from_name(device, k)].append((k,v))

        for tile, (pip, all_touched_coords) in design_set_no_nulls.items():
            tiletype_or_overlay = tile.split(":")[1]

            if pip is not None:
                owned_tiles_for_tiletype = {
                    tile: delta
                    for (r,c) in all_touched_coords
                    for tile,delta in rc_deltas.get((r, c), [])
                }

                (from_wire, to_wire) = pip

                wire_is_mux = \
                    ("MUXOUT" in to_wire or \
                    "CMUX_CORE_CMUX" in to_wire or \
                    to_wire.endswith("MIDMUX") or \
                    ("HPBX" in to_wire and "VPSX" in from_wire))

                anon_pip = make_anon_pip(tile, pip)

                if (tiletype_or_overlay, from_wire, to_wire) not in exclusion_list:
                    nfrom_wire = fix_name(from_wire)
                    nto_wire = fix_name(to_wire)

                    if not wire_is_mux:
                        try:
                            with (fuzzconfig.db_lock() as db):
                                def add_pip(changed_tile, delta):
                                    norm_from_wire, norm_to_wire = chip.normalize_wire(changed_tile.split(",")[0], nfrom_wire), \
                                        chip.normalize_wire(changed_tile.split(",")[0], nto_wire)

                                    logging.debug(f"Adding pip {changed_tile}({tile}) {nfrom_wire} -> {nto_wire} {delta} from {prefix}")
                                    transaction_log.info(
                                        f"{bitstream.vfiles} add_pip {device} {changed_tile}({tile}): {nfrom_wire} -> {nto_wire} {norm_from_wire} -> {norm_to_wire} Bits: {delta}")
                                    if changed_tile == tile:
                                        changed_tile = changed_tile + tile_suffix
                                    db.add_pip(chip, changed_tile, nfrom_wire, nto_wire, set(delta))

                                if tile not in owned_tiles_for_tiletype and len(owned_tiles_for_tiletype) > 0:
                                    logging.warning(f"Primary tile {tile} for {pip} {anon_pip} not in mod list: {owned_tiles_for_tiletype}")

                                for delta_tile, delta in owned_tiles_for_tiletype.items():
                                    anon_pip_delta_tiles[anon_pip].append((delta_tile, delta))
                                    add_pip(delta_tile, delta)

                                if len(owned_tiles_for_tiletype) == 0:
                                    empty_deltas[anon_pip] = (pip, tile)

                        except BaseException as e:
                            raise BitConflictException(device, nfrom_wire, nto_wire, tile, e)

                    else:
                        # Very niche carve out. When you enable a MUXINA wire to something without enabling any other
                        # wires in that mux group, radiant enables all of the MUXIND's by default on the unused arcs. So
                        # to correct for this, we just incorporate the knowledge that really those MUXINA connections are
                        # otherwise defaults (no bit changes)
                        if "MUXINA" in from_wire:
                            owned_tiles_for_tiletype = {k:[] for k in owned_tiles_for_tiletype}
                        mux_deltas[make_anon_node(tile, to_wire)][make_anon_node(tile, from_wire)] = (tile, owned_tiles_for_tiletype)

    if builder is not None: builder.reserve(len(design_sets) - 1)

    await asyncio.gather(*[
        asyncio.create_task(process_design(idx, design_set), name=f"{asyncio.current_task().get_name()}/process_design_{idx}")
        for idx, (design_set) in enumerate(design_sets)
    ])

    with (fuzzconfig.db_lock() as db):
        for anon_pip, ((from_wire, to_wire), tile) in empty_deltas.items():
            nfrom_wire = fix_name(from_wire)
            nto_wire = fix_name(to_wire)

            transaction_log.info(
                f"add_conn {device} {tile}: {nfrom_wire} ")

            if anon_pip in anon_pip_delta_tiles:
                (delta_tile, delta) = anon_pip_delta_tiles[0]
                if delta_tile == tile:
                    delta_tile = delta_tile + tile_suffix
                db.add_denormalized_conn(chip, delta_tile, nfrom_wire, nto_wire)
            else:
                delta_tile = tile + tile_suffix
                db.add_denormalized_conn(chip, delta_tile, nfrom_wire, nto_wire)


        for to_wire, from_wire_deltas in mux_deltas.items():
            (rel_tile, delta) = list(from_wire_deltas.values())[0]
            for concrete_tile, nfrom_wire, nto_wire, delta in generate_mux_deltas(device_tiles, to_wire, from_wire_deltas):
                norm_from_wire, norm_to_wire = chip.normalize_wire(rel_tile.split(",")[0], nfrom_wire), \
                    chip.normalize_wire(rel_tile.split(",")[0], nto_wire)

                logging.debug(f"Adding mux pip {rel_tile} {nfrom_wire} -> {nto_wire} {delta}")
                transaction_log.info(
                    f"add_pip {device} {rel_tile}: {nfrom_wire} -> {nto_wire} {norm_from_wire} -> {norm_to_wire} Bits: {delta}")

                if concrete_tile is None:
                    logging.error(f"Could not resolve concrete tile for {rel_tile}")
                assert (concrete_tile is not None)

                if concrete_tile == rel_tile:
                    concrete_tile = concrete_tile + tile_suffix

                try:
                    db.add_pip(chip, concrete_tile, nfrom_wire, nto_wire, set(delta))

                except BaseException as e:
                    raise BitConflictException(device, nfrom_wire, nto_wire, concrete_tile, e)



    with fuzzconfig.db_lock() as db:
        db.flush()

