import asyncio
import itertools
import logging
import random
import re
import time
import traceback
from collections.abc import Iterable
from functools import cache

from six import reraise

import database
from collections import defaultdict
import lapie

import cachecontrol
from radiant import validate_wire_list

pos_re = re.compile(r'R(\d+)C(\d+)')


def pos_from_name(tile):
    """
    Extract the tile position as a (row, column) tuple from its name
    """
    s = pos_re.search(tile)
    assert s
    return int(s.group(1)), int(s.group(2))

def type_from_fullname(tile):
    """
    Extract the type from a full tile name (in name:type) format
    """
    return tile.split(":")[1]

def get_rc_from_edge(device, side, offset):
    devices = database.get_devices()
    device_info = devices["families"][database.get_family_for_device(device)]["devices"][device]

    max_row = device_info["max_row"]
    max_col = device_info["max_col"]

    if side == "T":
        return (0, int(offset))
    elif side == "B":
        return (int(max_row), int(offset))
    elif side == "R":
        return (int(offset), int(max_col))
    elif side == "L":
        return (int(offset), 0)
    
    assert False, f"Could not match IO with side as side {side} offset {offset}"

def get_tiles_from_edge(device, side, offset = -1):
    (r, c) = get_rc_from_edge(device, side, offset)
    tg = database.get_tilegrid(device)["tiles"]

    return [t for t, tinfo in tg.items() if (c == -1 or tinfo["x"] == c) and (r == -1 or tinfo["y"] == r)]

def get_sites_from_primitive(device, primitive):
    sites = database.get_sites(device)    
    return {k:s for (k,s) in sites.items() if s['type'] == primitive}


def get_tiletypes(device):
    tilegrid = database.get_tilegrid(device)['tiles']
    tiletypes = defaultdict(list)
    for (k,v) in tilegrid.items():
        tiletypes[k.split(":")[-1]].append(k)
    return tiletypes

def get_tiles_by_filter(device, fn):
    tilegrid = database.get_tilegrid(device)['tiles']

    return {k:v for k,v in tilegrid.items() if fn(k, v)}
    

def get_tiles_by_tiletype(device, tiletype):
    tilegrid = database.get_tilegrid(device)['tiles']

    return {k: v for k, v in tilegrid.items() if k.split(":")[-1] == tiletype}

def get_coincidental_tiletypes_for_tiletype(device, tiletype):
    tt_t = get_tiles_by_tiletype(device, tiletype)
    rcs = [get_rc_from_name(device, t) for t in tt_t]
    tiles_at_rc = [{t.split(":")[-1] for t in get_tiles_by_rc(device, rc)} for rc in rcs]
    if len(tiles_at_rc) == 0:
        return {}

    s = tiles_at_rc[0]
    for tiletypes in tiles_at_rc:
        s = s & tiletypes
    s.remove(tiletype)

    return s


def get_tiles_by_primitive(device, primitive):
    tilegrid = database.get_tilegrid(device)['tiles']
    
    rc_regex = re.compile("R([0-9]*)C([0-9]*)")
    edge_regex = re.compile("IOL_(.)([0-9]*)")    
    sites = get_sites_from_primitive(device, primitive)

    tg_by_rc = { (t['y'], t['x']):(k, t) for (k, t) in tilegrid.items() }

    rcs = {}
    for (a,v) in sites.items():
        rc = get_rc_from_name(device, a)

        (name, t) = tg_by_rc[rc]
        rcs[(a,name)] = t

    return rcs

def get_tiletypes_by_primitive(device, primitive):
    tiles = get_tiles_by_primitive(device, primitive)

    rtn = defaultdict(list)
    for ((site,tilename),v) in tiles.items():
        tiletype = tilename.split(":")[1]
        rtn[tiletype].append((site, tilename, v))
    return rtn

def get_sites_for_tile(device, tile):
    tilegrid = database.get_tilegrid(device)['tiles']
    tile = [v for (k,v) in tilegrid.items() if k.startswith(tile) ][0]

    sites = database.get_sites(device)

    RC = (tile["y"], tile["x"])
    
    return {k:v for k,v in sites.items() if RC == get_rc_from_name(device, k)}

@cache
def get_full_node_set(device):
    all_nodes = lapie.get_full_node_list(device)
    return set([n for n in all_nodes if len(n)])

@cache
def get_node_list_lookups(device):
    _spine_regex = re.compile("(.)([0-9][0-9])[NEWS]([0-9][0-9])([0-9][0-9])")
    _hpbx_regex = re.compile("HPBX[0-9]*")

    node_list_lookup = defaultdict(list)
    node_owned_lookup = defaultdict(list)
    tile_owned_lookup = defaultdict(list)
    
    for name in lapie.get_full_node_list(device):
        if len(name) == 0: continue

        rc = get_rc_from_name(device, name)
        name_no_rc = "_".join(name.split("_")[1:])

        def get_owning_tiles_for_rc(rc):
            tiles = sorted([t for t in get_tiles_by_rc(device, rc)])

            for t in tiles:
                if ":PLC" in t:
                    return [t]

            if name_no_rc.startswith("HPBX"):
                for t in tiles:
                    if ":TAP" in t:
                        return [t]

            if len(tiles) > 1:
                tiles = [t for t in tiles if "TAP_" not in t and "EBR" not in t]

            return tiles

        tiles_at_rc = get_owning_tiles_for_rc(rc)

        if len(tiles_at_rc) == 0:
            tileless_rcs = set()

            # LIFCL-33 weirdness. Basically tiles at this RC don't actually exist, but there are nodes with the RC names.
            # We don't want to emit warnings about these. If other device/RC's are similar they should be added here.
            if device == "LIFCL-33U":
                tileless_rcs = set(["R37C52_H01E0100", "R73C160_JIVREFI4_IVREF_CORE"])

            if name not in tileless_rcs:
                logging.warning(f"Could not find tiles for {device} {rc} {name} {[t for t in get_tiles_by_rc(device, rc)]}")
            continue

        if rc is None:
            continue

        elif rc[0] < 0 or rc[1] < 0:
            logging.warning(f"Nodename {name} has negative rc: {rc}")

        for tile in tiles_at_rc: node_list_lookup[tile].append(name)

        m = _spine_regex.match(name_no_rc)

        if m is not None:
            owners = list(resolve_possible_names(device, name))
            for owner in owners:
                tiles_at_rc = get_owning_tiles_for_rc(get_rc_from_name(device, owner))
                if len(tiles_at_rc) > 0:
                    break

            if len(tiles_at_rc) != 1:
                tiles_at_rc = sorted(tiles_at_rc, key=lambda t: len(t))

            node_owned_lookup[tiles_at_rc[0]].append(name)
            tile_owned_lookup[name].extend(tiles_at_rc)            
        elif _hpbx_regex.search(name_no_rc) is not None:
            tap_tiles_on_r = sorted([(abs(rc[1] - get_rc_from_name(device, x)[1]), x)
                        for x in get_tiles_by_filter(device, lambda _, info: info["y"] == rc[0]) if ":TAP" in x])
            owner = next(iter([tile for tile in tap_tiles_on_r]), None)[1]

            if owner is not None:
                node_owned_lookup[owner].append(name)
                tile_owned_lookup[name].append(owner)
            else:
                logging.warning(f"Could not find owner for {name}: {lapie.get_node_data(device, name)[0].aliases} {tap_tiles_on_r}")
        else:
            node_owned_lookup[tiles_at_rc[0]].append(name)
            tile_owned_lookup[name].extend(tiles_at_rc)

    return node_list_lookup, node_owned_lookup, tile_owned_lookup

def get_tile_list_for_node(device, node):
    _, _, tile_owned_lookup = get_node_list_lookups(device)

    return tile_owned_lookup[node]

def get_node_list_for_tile(device, tile, owned = False):
    node_list_lookup, node_owned_lookup, _ = get_node_list_lookups(device)

    def _get_node_list_for_tile(t):
        return (node_owned_lookup if owned else node_list_lookup).get(t, [])

    if isinstance(tile, list):
        return {n:t for t in tile for n in _get_node_list_for_tile(t)}
    else:
        return _get_node_list_for_tile(tile)

def get_nodes_for_tile(device, tile, owned = False):
    if isinstance(tile, list):
        nodes2tile = {n:t for t in tile for n in get_node_list_for_tile(device, t, owned)}
        node_info = {n.name:n for n in lapie.get_node_data(device, list(nodes2tile.keys()), False)}

        tile_nodes = defaultdict(dict)
        for n, ninfo in node_info.items():
            tile_nodes[nodes2tile[n]][n.name] = ninfo        
        
        return tile_nodes
    else:
        tile_nodes = get_node_list_for_tile(device, tile, owned)
        if len(tile_nodes) == 0:
            return {}
    
        return {n.name:n for n in lapie.get_node_data(device, tile_nodes, False)}

_get_tiles_by_rc = {}
def get_tiles_by_rc(device, rc = None):
    if isinstance(rc, str):
        rc = get_rc_from_name(device, rc)

    if device not in _get_tiles_by_rc:
        tilegrid = database.get_tilegrid(device)['tiles']
        _get_tiles_by_rc[device] = defaultdict(dict)
        for k,v in tilegrid.items():
            nrc = (v['y'], v['x'])
            _get_tiles_by_rc[device][nrc][k] = v

    return _get_tiles_by_rc[device][rc]



def get_tile_routes(device, tilename, owned = False):
    node_data = get_nodes_for_tile(device, tilename, owned = owned)

    return node_data

rc_regex = re.compile("R([0-9]+)C([0-9]+)")
edge_regex = re.compile("IOL_(.)([0-9]+)")
_get_rc_from_name_lookup = {}
def get_rc_from_name(device, name):
    if isinstance(name, tuple):
        return name

    if name[:6] in _get_rc_from_name_lookup:
        return _get_rc_from_name_lookup[name[:7]]

    m = rc_regex.search(name)
    if m:
        rc = (int(m.group(1)), int(m.group(2)))
        if m.start() == 0:
            _get_rc_from_name_lookup[name[:7]] = rc
        return rc

    m = edge_regex.match(name)
    if m:
        return get_rc_from_edge(device, m.group(1), m.group(2))

    if name not in ["R", "L"] and not name.startswith("DCC"):
        logging.warning(f"Could not derive RC from {name}")
    return None

def get_tile_from_node(device, node):
    rc = get_rc_from_name(device, node)
    tilegrid = database.get_tilegrid(device)['tiles']

    for k,v in tilegrid.items():
        if (v['y'], v['x']) == rc:
            return k

def get_connected_nodes(device, tilename):
    routes = get_tile_routes(device, tilename)

    def tile_route(route):    
        return list(set([
            wire
            for (n,r) in route.items()
            for p in r.pips()
            for wire in [p.from_wire, p.to_wire]
        ]))
        
    
    if isinstance(tilename, list):
        return {t:tile_route(route) for t,route in routes.items()}

    print(routes)
    return tile_route(routes)
        

def get_pins_for_site(device, site):
    sites = database.get_sites(device)
    site_info = sites[site]

    nodes = {n.name:n for n in lapie.get_node_data(device, [p['pin_node'] for p in site_info['pins']])}

    return [(p, nodes[p['pin_node']]) for p in site_info['pins']]
    
def get_pips_for_tile(device, tilename, owned = False, dir = None):
    assert(dir is None or dir == "uphill" or dir == "downhill")

    def pips(r):
        if dir is None:
            return r.pips()
        elif dir == "uphill":
            return r.uphill_pips
        elif dir == "downhill":
            return r.downhill_pips
    
    routes = get_tile_routes(device, tilename, owned = owned)
    return list(set([
        (p.from_wire,
         p.to_wire)
        for (n,r) in routes.items()
        for p in pips(r)
    ]))

def get_connected_tiles(device, tilename):    
    connected_nodes = get_connected_nodes(device, tilename)
    
    tilegrid = database.get_tilegrid(device)['tiles']
    
    rcs = set([get_rc_from_name(device, n) for n in connected_nodes])
    
    return { k:v for k,v in tilegrid.items() if (v['y'], v['x']) in rcs  }

def draw_rc(device, rcs):
    devices = database.get_devices()
    device_info = devices["families"][database.get_family_for_device(device)]["devices"][device]

    max_row = device_info["max_row"]
    max_col = device_info["max_col"]

    rcs = set(rcs)
    for y in range(0, max_col):
        for x in range(0, max_row):
            print("■" if (x,y) in rcs else "☐" , end='')
        print()

def get_wires_for_tiles(device):
    anon_nodes = defaultdict(lambda : defaultdict(list))
    for n in get_full_node_set(device):
        wire_name = "_".join(n.split("_")[1:])
        rc = get_rc_from_name(device, n)
        for tile in sorted(get_tiles_by_rc(device, rc)):
            tiletype = tile.split(":")[-1]
            anon_nodes[tiletype][wire_name].append(tile)

    return anon_nodes

def get_wires_for_sites(device):
    anon_nodes = defaultdict(lambda : defaultdict(list))
    sites = database.get_sites(device)

    for site, site_info in sites.items():
        pins = site_info['pins']
        pin_nodes = [p["pin_node"] for p in pins]

        for n in pin_nodes:
            wire_name = "_".join(n.split("_")[1:])
            rc = get_rc_from_name(device, n)

            anon_nodes[site_info["type"]][wire_name].append(site)
    return anon_nodes

def get_representative_nodes_data(device, seed = 42, exclude_set = []):
    rep_nodes = get_wires_for_tiles(device)
    nodes = []
    random.seed(42)

    lookup = {}
    for tiletype, wire_dict in sorted(rep_nodes.items()):
        if tiletype not in exclude_set:
            for wire, tiles in sorted(wire_dict.items()):
                tile = random.choice(tiles)
                (r,c) = get_rc_from_name(device, tile)
                wire_name = f"R{r}C{c}_{wire}"
                nodes.append(f"R{r}C{c}_{wire}")
                lookup[wire_name] = (tiletype, wire, tile)

    nodes = sorted(nodes)

    batches = list(itertools.batched(nodes, 5000))
    batch_returns = [None] * len(batches)

    def f(idx_batch):
        (idx, batch) = idx_batch
        batch_returns[idx] = lapie.get_node_data(device, list(batch))

    import fuzzloops
    fuzzloops.parallel_foreach(enumerate(batches), f, jobs=len(batches))

    node_data = {a:v
                 for d in batch_returns
                 for v in d
                 for a in v.aliases}

    rtn = defaultdict(list)
    for wire_name, lu in lookup.items():
        rtn[lu[0]].append((lu[2], node_data[wire_name]))

    return rtn

def get_node_data_local_graph(device, node, should_expand = None):
    if isinstance(node, Iterable):
        node = list(node)

    if not isinstance(node, list):
        node = [node]

    rc = get_rc_from_name(device, node[0])
    def def_should_expand(node):
        return rc == get_rc_from_name(device, node)

    if should_expand is None:
        should_expand = def_should_expand

    query_list = node

    graph = {}
    while len(query_list) > 0:
        new_nodes = lapie.get_node_data(device, query_list)
        graph.update({n.name:n for n in new_nodes})

        query_list = [wire for n in new_nodes
                      for p in n.pips()
                      for wire in [p.to_wire, p.from_wire]
                      if wire not in graph and should_expand(wire)]

    return graph

def get_local_pips_for_site(device, site, include_interface_pips = True):
    if isinstance(site, str):
        sites = database.get_sites(device)
        site = sites[site]

    site_nodes = [p["pin_node"] for p in site["pins"]]

    return get_local_pips_for_nodes(device, site_nodes,
                                    include_interface_pips = include_interface_pips,
                                    should_expand = lambda x: site["type"] in x)

def get_local_pips_for_nodes(device, nodes, should_expand = None, include_interface_pips = True, executor = None):
    if executor is not None:
        return executor.submit(get_local_pips_for_nodes, device, nodes, should_expand = should_expand ,include_interface_pips = include_interface_pips)

    local_graph = get_node_data_local_graph(device, nodes, should_expand = should_expand)

    def should_include(p):
        if include_interface_pips:
            return p.from_wire in local_graph or p.to_wire in local_graph
        else:
            return p.from_wire in local_graph and p.to_wire in local_graph

    pips = [(p.from_wire, p.to_wire)
            for n, info, in local_graph.items()
            for p in info.pips() if
            should_include(p)]

    return sorted(set(pips)), local_graph

async def get_tiles_with_pip(device, pip, tiles = None, pips_by_node = None):
    if tiles is None:
        tilegrid = database.get_tilegrid(device)['tiles']
        tiles = {k:get_rc_from_name(device, k) for k, v in tilegrid.items()}
    else:
        tiles = {k:get_rc_from_name(device, k) for k in tiles}

    def has_pip_nodes(rc):
        nodes = tuple([resolve_actual_node(device, w, rc) for w in pip])
        if any([n is None for n in nodes]):
            return None
        return nodes

    rtn = {actual_pip:k for k,rc in tiles.items() if (actual_pip := has_pip_nodes(rc)) is not None}

    if pips_by_node is None:
        pips_by_node = await lapie.get_pip_data(device, [n[0] for n in rtn])

    return {v for k,v in rtn.items() if k in pips_by_node}

async def get_pip_tile_groupings_for_tiletype(device, tiletype, owned=True):
    ts = sorted(list(get_tiles_by_tiletype(device, tiletype).keys()))

    return await get_pip_tile_groupings(device, ts)

@cachecontrol.cache_fn()
async def get_pip_tile_groupings(device, tiles):
    import interconnect
    import fuzzconfig
    import fuzzloops

    ts = tiles

    all_nodes = {
        node:tile
        for tile in ts
        for node in get_node_list_for_tile(device, tile, owned=True)
    }

    all_pips = set(await lapie.get_pip_data(device, list(all_nodes.keys()), filter_type="to"))

    pips_by_tile = defaultdict(set)
    for p in all_pips:
        w = p[1]
        if w in all_nodes:
            pips_by_tile[all_nodes[w]].add(p)

    tiles_with_rel_pips = defaultdict(set)

    def relative_node(n, rc):
        rel_node = resolve_relative_node(device, n, rc)
        return rel_node

    for t, absolute_pips in pips_by_tile.items():
        # Yield
        await asyncio.sleep(0)

        rc = get_rc_from_name(device, t)
        rc_pips = set([
            tuple([relative_node(n, rc) for n in p])
            for p in absolute_pips
        ])

        for anon_pip in rc_pips:
            tiles_with_rel_pips[anon_pip].add(t)

    rel_pip_groups = defaultdict(set)
    for anon_pip, tiles in tiles_with_rel_pips.items():
        rel_pip_groups[tuple(sorted(tiles))].add(anon_pip)

    return rel_pip_groups

@cachecontrol.cache_fn()
def get_representative_nodes_for_tiletype(device, tiletype, owned = True):
    node_set = get_representative_nodes_for_tiles(device, get_tiles_by_tiletype(device, tiletype), owned = owned)

    coincidental_tiletypes = get_coincidental_tiletypes_for_tiletype(device, tiletype)
    for ctt in coincidental_tiletypes:
        ctt_nodes = get_representative_nodes_for_tiletype(device, ctt, owned = owned)
        node_set = node_set - ctt_nodes

    return node_set

def get_representative_nodes_for_tiles(device, tiles, owned = True, union = False):
    node_set = None

    for tile in tiles:
        tile_rc = get_rc_from_name(device, tile)
        nodes = set(resolve_relative_node(device, n, tile_rc) for n in get_node_list_for_tile(device, tile, owned))
        if node_set is None:
            node_set = nodes
        else:
            if union:
                node_set = node_set | nodes
            else:
                node_set = node_set & nodes
    if node_set is None:
        return set()

    return node_set

def get_outlier_nodes_for_tiletype(device, tiletype):
    repr_nodes = get_representative_nodes_for_tiletype(device, tiletype)

    outliers = {}
    for tile in get_tiles_by_tiletype(device, tiletype):
        nodes = set(["_".join(n.split("_")[1:]) for n in get_node_list_for_tile(device, tile)])

        node_outliers = nodes - repr_nodes

        if len(node_outliers) > 0:
            outliers[tile] = node_outliers

    return outliers

@cachecontrol.cache_fn()
def get_connections_for_device(device):
    arcs = lapie.get_jump_wires(device)

    connections = defaultdict(set)
    for frm, to in arcs:
        connections[frm].add(to)

    return connections

def find_path(device, frm, to):
    nodes = lapie.get_node_data(device, [frm])

    edges = {}
    visited = set()
    found = False
    while not found:
        query = set()
        for n in nodes:
            for p in n.uphill_pips:
                if p.to_wire == to:
                    found = True
                    break

                if p.to_wire not in visited:
                    edges[p.to_wire] = n
                    visited.add(p.to_wire)
                    query.add(p.to_wire)
        nodes = lapie.get_node_data(device, query)

    path = []
    c = to
    while c != frm:
        path.append(c)
        c = edges[c]
    return path

_resolve_relative_node_regex = re.compile(r"([HV])0(\d)([NEWS])0([0-9])0([0-9])")
def resolve_relative_node(device, n, rel_to = (0,0)):
    if isinstance(rel_to, str):
        rel_to = get_rc_from_name(device, rel_to)
    (rr, cc) = rel_to

    rc = get_rc_from_name(device, n)
    if rc is None:
        logging.warning(f"Can not resolve relative node for {n}")
        return None

    (r,c) = rc

    wire = "_".join(n.split("_")[1:])

    global_prefixes = ["VCC", "VPSX", "LHPRX", "RHPRX"]

    if any([wire.startswith(prefix) for prefix in global_prefixes]):
        return (f"G:{wire}", (r, c))

    fixed_column_prefixes = ["HPBX", "HPRX"]

    if any([wire.startswith(prefix) for prefix in fixed_column_prefixes]):
        return (f"C:{wire}", (r-rr, c))

    # if wire.startswith("HPBX"):
    #     return ("B:", wire.split("HPBX")[-1])

    match = _resolve_relative_node_regex.search(n)
    if match:
        (orientation, length, direction, slot, tap) = match.groups()
        (length, slot, tap) = (int(length), int(slot), int(tap))

        canon_tap = 0
        offset = (tap - canon_tap)
        if direction in "SE":
            offset = -offset

        d = (offset + r-rr, c-cc)
        if orientation == 'H':
            d = (r-rr, offset + c-cc)
        return (direction, d, length, slot)

    return (wire, (r-rr, c-cc))

def resolve_node_rcs(device, n):
    if isinstance(n, str):
        orig_n = n
        n = resolve_relative_node(device, n)

    if n is None:
        return []

    (wire_type, rc, *args) = n

    if wire_type in "NEWS":
        def resolve_possible_names(n):
            (direction, rc, length, slot) = n
            (r, c) = (rc[0], rc[1] )

            for i in range(length + 1):
                diri = i if direction in "SE" else -i
                nc = c + diri if direction in "EW" else c
                nr = r + diri if direction in "NS" else r

                yield (nr, nc)
        return [n for n in resolve_possible_names(n)]
    return [rc]

def resolve_possible_names(device, n, rel_to=(0,0)):
    if isinstance(n, str):
        orig_n = n
        n = resolve_relative_node(device, n)

    (direction, rc, length, slot) = n
    orientation = "H" if direction in "EW" else "V"
    for i, (rr,cc) in enumerate(resolve_node_rcs(device, n)):
        nr = rr + rel_to[0]
        nc = cc + rel_to[1]
        if nr >= 0 and nc >= 0:
            yield f"R{nr}C{nc}_{orientation}0{length}{direction}0{slot}0{i}"

def is_edge_node(device, n):
    rcs = resolve_node_rcs(device, n)
    devices = database.get_devices()
    device_info = devices["families"][database.get_family_for_device(device)]["devices"][device]

    max_row = device_info["max_row"]
    max_col = device_info["max_col"]

    return any([(r >= max_row or r <= 0 or c >= max_col or c <= 0) for (r,c) in rcs])

def resolve_actual_node(device, n, rel_to = (0,0)):
    if isinstance(rel_to, str):
        rel_to = get_rc_from_name(device, rel_to)

    (wire_type, rc, *args) = n

    if wire_type in "NEWS":
        def resolve_possible_names(n):
            (direction, rc, length, slot) = n
            orientation = "H" if direction in "EW" else "V"
            for i, (rr,cc) in enumerate(resolve_node_rcs(device, n)):
                nr = rr + rel_to[0]
                nc = cc + rel_to[1]
                yield f"R{nr}C{nc}_{orientation}0{length}{direction}0{slot}0{i}"

        fullnodes = get_full_node_set(device)
        existing_nodes = [n for n in resolve_possible_names(n) if n in fullnodes]

        assert(len(existing_nodes) < 2)
        if len(existing_nodes) == 0:
            logging.debug(f"No nodes found for {n} {rel_to}")
        return next(iter(existing_nodes), None)

    if wire_type.startswith("G:"):
        (r,c) = rc
        return f"R{r}C{c}_{wire_type.split(":")[1]}"

    if wire_type.startswith("B:"):
        print(f"{n} relative to {rel_to}")
        assert (False)

    if wire_type.startswith("C:"):
        (r,c) = (rc[0] + rel_to[0], rc[1])
        return f"R{r}C{c}_{wire_type.split(":")[1]}"

    (r,c) = (rc[0] + rel_to[0], rc[1] + rel_to[1])
    if (r < 0) or c < 0:
        return None
    return f"R{r}C{c}_{wire_type}"


class TilesHelper:
    def __init__(self, device):
        self.device = device

    def rc_sub(self, a, b):
        device = self.device
        if isinstance(a, str): a = get_rc_from_name(device, a)
        if isinstance(b, str): b = get_rc_from_name(device, b)
        return (a[0] - b[0], a[1] - b[1])

    def rc_add(self, a, b):
        device = self.device
        if isinstance(a, str): a = get_rc_from_name(device, a)
        if isinstance(b, str): b = get_rc_from_name(device, b)
        return (a[0] + b[0], a[1] + b[1])

    @cache
    def chip(self):
        import fuzzconfig
        return fuzzconfig.FuzzConfig.standard_chip(self.device)

    def make_tile_unanon(self, anon_tile, rel_to):
        return sorted({get_rc_from_name(self.device, t) for t in self.resolve_anon_tile(anon_tile, rel_to)})

    def get_related_tiles(self, anon_tile, rel_to):
        tiletype = anon_tile[0]

        unique_prefixes = ["PCLK_DLY", "DDR_OSC", "IO_", "SYSIO_", "TMID_", "BMID_", "GPLL_", "DLY"]
        for unique_prefix in unique_prefixes:
            if tiletype.startswith(unique_prefix):

                def match_by_r_and_tiletype(_, tile_info):
                    return tile_info['tiletype'].startswith(unique_prefix)  # and rel_to[0] == tile_info['y']

                return get_tiles_by_filter(self.device, match_by_r_and_tiletype)

        return self.resolve_anon_tile(anon_tile, rel_to)

    def make_tile_anon(self, tile, rel_to):
        device = self.device

        if isinstance(rel_to, str):
            rel_to = get_rc_from_name(device, rel_to)

        tiletype = tile.split(":")[-1]
        rc = get_rc_from_name(device, tile)
        if "TAP" in tiletype:
            return f"C:{tiletype}", rc[1]
        #
        # unique_prefixes = ["PCLK_DLY", "DDR_OSC", "IO_", "SYSIO_", "TMID_", "BMID_"]
        # for unique_prefix in unique_prefixes:
        #     if tiletype.startswith(unique_prefix):
        #         def unanon_fn(rel_to):
        #             def match_by_r_and_tiletype(_, tile_info):
        #                 return tile_info['tiletype'].startswith(unique_prefix)  # and rel_to[0] == tile_info['y']
        #
        #             return get_tiles_by_filter(device, match_by_r_and_tiletype)
        #
        #         return unanon_fn

        return tiletype, self.rc_sub(rc, rel_to)

    def resolve_anon_tile(self, anon_tile, rel_to):
        device = self.device
        if isinstance(rel_to, str):
            rel_to = get_rc_from_name(device, rel_to)

        if callable(anon_tile):
            return anon_tile(rel_to)

        (type, x) = anon_tile

        if type.startswith("C:"):
            match_rc = (rel_to[0], x)
            match_type = type.split(":")[-1]
        else:
            match_rc = self.rc_add(rel_to, x)
            match_type = type

        return [t for t in get_tiles_by_rc(device, match_rc) if t.split(":")[-1] == match_type]
