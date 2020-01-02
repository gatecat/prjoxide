from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="EBRROUTE0", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C15:EBR_1", "CIB_R29C16:EBR_2", "CIB_R29C14:MIB_EBR"]),
        "rc": (28, 14),
    },
    {
        "cfg": FuzzConfig(job="EBRROUTE1", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C18:EBR_4", "CIB_R29C19:EBR_5", "CIB_R29C17:MIB_EBR"]),
        "rc": (28, 17),
    },
    {
        "cfg": FuzzConfig(job="EBRROUTE2", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C21:EBR_7", "CIB_R29C22:EBR_8", "CIB_R29C23:EBR_9", "CIB_R29C24:EBR_10", "CIB_R29C20:MIB_EBR"]),
        "rc": (28, 20),
    },
    {
        "cfg": FuzzConfig(job="EBRROUTE3", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C23:EBR_9", "CIB_R29C21:EBR_7", "CIB_R29C22:EBR_8", "CIB_R29C24:EBR_10", "CIB_R29C20:MIB_EBR"]),
        "rc": (28, 22),
    },
]

ignore_tiles = set([
    "CIB_R28C{}:CIB".format(c) for c in range(14, 27)
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
