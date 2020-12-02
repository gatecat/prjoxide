from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="LRAMROUTE0", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R23C87:LRAM_0"]),
        "rc": (18, 86),
    },
    {
        "cfg": FuzzConfig(job="LRAMROUTE1", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R41C87:LRAM_1"]),
        "rc": (40, 86),
    },
]

ignore_tiles = set([
    "CIB_R{}C86:CIB_LR".format(c) for c in range(2, 55)
] + [
    "CIB_R19C86:CIB_LR_A",
    "CIB_R20C86:CIB_LR_B",
    "CIB_R28C86:CIB_LR_A",
    "CIB_R37C86:CIB_LR_A",
    "CIB_R46C86:CIB_LR_A",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("LRAM_CORE" in x)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
