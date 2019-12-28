from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="EBRROUTE0", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C15:EBR_1", "CIB_R29C16:EBR_2", "CIB_R29C14:MIB_EBR"]),
        "rc": (28, 14),
    },
]

ignore_tiles = set([
    "CIB_R28C14:CIB",
    "CIB_R28C15:CIB",
    "CIB_R28C16:CIB",
    "CIB_R28C17:CIB",
    "CIB_R28C18:CIB",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("EBR_CORE" in x)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
