from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
from interconnect import fuzz_interconnect, fuzz_interconnect_pins
import tiles

from primitives import oscd_core

cfgs = [
    FuzzConfig(job="OSCD", device="LIFCL-33U", tiles=["CIB_R0C29:OSCD"]),
]

def main():
    for cfg in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "oscd.v"

        def bin_to_int(x):
            val = 0
            mul = 1
            for bit in x:
                if bit:
                    val |= mul
                mul *= 2
            return val

        sites = tiles.get_sites_from_primitive(cfg.device, "OSCD_CORE")
        site = list(sites.keys())[0]
        
        def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False):
            if kv is None:
                config = ""
            elif mux:
                val = "#SIG"
                if kv[1] in ("0", "1"):
                    val = kv[1]
                if kv[1] == "INV":
                    val = "#INV"
                config = "{}::::{}={}".format(mode, kv[0], val)
            else:
                config = "{}:::{}={}".format(mode, kv[0], kv[1])
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site)

        nonrouting.fuzz_primitive_definition(cfg, empty, site, oscd_core)

        cfg.sv = "../shared/route.v"
        regex = True
        nodes = [".*_OSCD_CORE" ]
        full_mux = True

        fuzz_interconnect(config=cfg, nodenames=nodes, regex=regex, bidir=True, full_mux_style=full_mux)

        
if __name__ == '__main__':
    fuzzloops.FuzzerMain(main)

