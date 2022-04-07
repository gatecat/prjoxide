from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="PLLULC", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C1:GPLL_ULC"]),
        "rc": (1, 1),
    },
    {
        "cfg": FuzzConfig(job="PLLLLC", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R55C0:GPLL_LLC"]),
        "rc": (55, 1),
    },
    {
        "cfg": FuzzConfig(job="PLLLRC", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R53C87:GPLL_LRC"]),
        "rc": (53, 86),
    },
    {
        "cfg": FuzzConfig(job="PLLLLC_15K", device="LIFCL-17", sv="../shared/route_17.v", tiles=["CIB_R29C1:GPLL_LLC_15K"]),
        "rc": (28, 1),
    },
    {
        "cfg": FuzzConfig(job="PLLLRC_15K", device="LIFCL-17", sv="../shared/route_17.v", tiles=["CIB_R29C74:GPLL_LRC_15K"]),
        "rc": (28, 74),
    },
]

ignore_tiles = set([
    "CIB_R50C86:CIB_LR"
    "CIB_R51C86:CIB_LR",
    "CIB_R52C86:CIB_LR",
    "CIB_R53C86:CIB_LR",
    "CIB_R54C86:CIB_LR",
    "CIB_R55C86:CIB",

    "CIB_R55C3:CIB",
    "CIB_R55C2:CIB",
    "CIB_R55C1:CIB",
    "CIB_R54C1:CIB_LR",
    "CIB_R53C1:CIB_LR",
    "CIB_R52C1:CIB_LR",

    "CIB_R1C3:CIB_T"
    "CIB_R1C2:CIB_T",
    "CIB_R1C1:CIB_T",
    "CIB_R2C1:CIB_LR",
    "CIB_R3C1:CIB_LR",
])

ignore_tiles_17 = set([
    "CIB_R26C74:CIB_LR",
    "CIB_R27C74:CIB_LR",
    "CIB_R28C74:CIB",
    "CIB_R28C73:CIB",
    "CIB_R28C72:CIB",
    "CIB_R26C1:CIB_LR",
    "CIB_R27C1:CIB_LR",
    "CIB_R28C1:CIB",
    "CIB_R28C2:CIB",
    "CIB_R28C3:CIB",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        ignore = ignore_tiles
        if cfg.device == "LIFCL-17":
            ignore = ignore_tiles_17
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("PLL_CORE" in x or "REFMUX_CORE" in x or "FBMUX_CORE" in x)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True,
        ignore_tiles=ignore)

if __name__ == "__main__":
    main()
