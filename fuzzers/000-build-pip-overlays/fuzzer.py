import hashlib
import itertools
import json
import logging
import os
import pprint
import traceback
from functools import cache

from fuzzconfig import FuzzConfig
import interconnect
import re
import database
import tiles
import random
import fuzzloops
import fuzzconfig
import lapie
import libpyprjoxide
import asyncio
from collections import defaultdict

from DesignFileBuilder import UnexpectedDeltaException, DesignFileBuilder, BitConflictException

### This fuzzer maps all of the pips in each device. It does this by anonymizing the pips for every tile, and generating
### common groupings which share pip definitions. A grouping of common pips is writen to an overlay file and we track
### which tiles containe which overlays.
###
### Currently the overlays are also keyed by tile type and in certain cases by device.
###
### To get the pips for every tile, the first thing this fuzzer does is download the node database from lark/lapie tools.
### This is pretty slow -- expect 2-3 hours per device -- but the results are cached into a sqlite database so this is
### a one time thing.
###
### To minimize the number of bitstreams built, this fuzzer uses DesignFileBuilder. This construct can combine multiple
### PIPs to solve into a single design. This brings the total number of bitfiles needed from around 20k per device to
### 2-3k per device.


### The hash in python isn't stable, so we generate our own to name the overlays unqiuely.
def stablehash(x):
    def set_default(obj):
        if isinstance(obj, set):
            return sorted(obj)
        raise TypeError

    bytes_data = json.dumps(x, sort_keys=True, default=set_default).encode('utf-8')

    hasher = hashlib.new("sha1")
    hasher.update(bytes_data)

    return hasher.hexdigest()

def make_dict_of_lists(lst, key):
    rtn = defaultdict(list)
    for item in lst:
        rtn[key(item)].append(item)
    return rtn

def make_overlay_name(k):
    (anon_pips, *args) = k
    return "-".join([*args, stablehash(anon_pips)])

async def FuzzAsync(executor):
    families = database.get_devices()["families"]
    devices = [
        device
        for family in families
        for device in families[family]["devices"]
        if fuzzconfig.should_fuzz_platform(device)
    ]

    for device in devices:
        tilegrid = database.get_tilegrid(device)['tiles']

        all_tiles = sorted({k for k in tilegrid})

        # Map of tiles group -> pip grouping
        rel_pip_groups = await tiles.get_pip_tile_groupings(device, all_tiles)

        pips_to_tiles = defaultdict(list)
        for ts, pips in rel_pip_groups.items():
            for pip in pips:
                for t in ts:
                    pips_to_tiles[pip].append(t)

        rel_pip_groups_by_tiletype = defaultdict(set)

        for pip,ts in pips_to_tiles.items():
            for tile_type, tt_ts in make_dict_of_lists(ts, lambda x: x.split(":")[-1]).items():
                rel_pip_groups_by_tiletype[tuple(sorted(tt_ts))].add(pip)

        def pip_is_tiletype_dependent(p):
            # Currently we seperate everything out by tiletype; but this might be unnecessary in some cases.
            return True

        overlays = {}
        for ts, anon_pips in rel_pip_groups_by_tiletype.items():
            assert (len(ts) == len(set(ts)))
            assert (len(anon_pips) == len(set(anon_pips)))
            for needs_tt, split_anon_pips in make_dict_of_lists(sorted(set(anon_pips)), pip_is_tiletype_dependent).items():
                split_anon_pips = sorted(split_anon_pips)

                if needs_tt:
                    for tt, grp in make_dict_of_lists(ts, lambda x: x.split(":")[-1]).items():
                        grp = sorted(grp)

                        overlay_args = [tt]

                        # TAP_CIB has conflicts amongst devices; so add device to the overlay key
                        if tt == "TAP_CIB":
                            overlay_args.append(device)

                        overlays[(tuple(sorted(split_anon_pips)), *overlay_args)] = grp
                else:
                    overlays[(tuple(sorted(split_anon_pips)), )] = sorted(ts)

        fuzzconfig.register_device_overlays(device, "000-build-pip-overlays", overlays)

        builder = DesignFileBuilder(device, executor)

        async def interconnect_group(overlay_key, ts):
            (anon_pips, *args) = overlay_key
            overlay = make_overlay_name(overlay_key)

            fn = database.get_cache_dir() + f"/pip-overlays-sigs/{device}/{overlay}.txt"
            os.makedirs(database.get_cache_dir() + f"/pip-overlays-sigs/{device}", exist_ok=True)
            if not os.path.exists(fn):
                with open(fn, "w") as f:
                    logging.warning(f"New pip grouping {fn}")
                    print(overlay_key,file=f)
                    print("\n",file=f)
                    print(ts,file=f)
                    print("\n",file=f)

            config = FuzzConfig(job=f"pip-overlays", device=device, tiles=ts)
            return await interconnect.fuzz_interconnect_sinks_across_span(config, ts, anon_pips, executor=executor, overlay=overlay, check_pip_placement=False, builder=builder)

        logging.info(f"Overlay count: {len(overlays)}")

        try:
            async with asyncio.TaskGroup() as tg:
                for k, v in sorted(overlays.items()):
                    tg.create_task(interconnect_group(k, v), name=f"interconnect_group_{make_overlay_name(k)}")
                tg.create_task(builder.build_task())
        except* UnexpectedDeltaException as egrp:
            logging.error(f"Caught an exception group for unexpected deltas: {egrp} {egrp.exceptions}")
            for e in egrp.exceptions:
                await e.find_bad_design(executor)
            raise
        except* BitConflictException as egrp:
            logging.error(f"Caught an exception group for bit conflicts: {egrp} {egrp.exceptions}")
            for e in egrp.exceptions:
                await e.solve_standalone()
            raise
        except* BaseException as eg:
            logging.error(f"Caught an exception group for base: {eg} {eg.exceptions}")
            for e in eg.exceptions:
                traceback.print_exception(e)
            raise

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(FuzzAsync)

