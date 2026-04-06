from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import database
from primitives import lram_core
import tiles
from tqdm.asyncio import tqdm
import asyncio

def create_device_lram_configs(device):
    # Find all the tiles where the LRAM_CORE primitive lives
    bel_tiles = sorted(tiles.get_tiles_by_primitive(device, "LRAM_CORE").keys(), key = lambda x: tiles.get_rc_from_name(device, x[0]))
    print("bel", device, bel_tiles, list(enumerate(bel_tiles)))

    # All the LRAM's have different tiles which do the configuration. These are the LRAM_* tile types
    lram_config_tiles = list(tiles.get_tiles_by_filter(device, lambda k,v: v["tiletype"].startswith("LRAM_")).keys())
    
    return [(bel_site, lram, FuzzConfig(job=bel_site, device=device, tiles=[bel_tile] + lram_config_tiles))
            for (lram,(bel_site,bel_tile)) in enumerate(bel_tiles)
        ]
    

configs = [cfg
           for device in database.get_device_list() if device.startswith("LIFCL")
           for cfg in create_device_lram_configs(device)]

def main():
    def per_config(x):
        site, lram_idx, cfg = x
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "lram.v"

        lram = f"LRAM{lram_idx}"
        def get_substs(mode="NONE", kv=None):
            if kv is None:
                config = ""
            else:
                key = kv[0]
                if key.endswith("MUX"):
                    key = ":" + key[:-3]                    
                config = f"{mode}:::{key}={kv[1]}"
            return dict(cmt="//" if mode == "NONE" else "",
                        config=config,
                        site=site)

        for setting in lram_core.settings:
            subs_fn = lambda x,name=setting.name: get_substs(mode="LRAM_CORE", kv=(name, x))
            if setting.name == "MODE":
                subs_fn = lambda x: get_substs(mode=x)

            mark_relative_to = None
            if cfg.tiles[0] != cfg.tiles[-1]:
                mark_relative_to = cfg.tiles[0]
                nonrouting.fuzz_enum_setting(cfg, empty, f"{lram}.{setting.name}", setting.values,
                                             subs_fn,
                                             False,
                                             desc=setting.desc, mark_relative_to=mark_relative_to)


    fuzzloops.parallel_foreach(configs, per_config)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
