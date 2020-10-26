from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="ECLK0", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C48:ECLK_0", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 48),
    },
    {
        "cfg": FuzzConfig(job="ECLK1", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C48:ECLK_0", "CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 49),
    },
    {
        "cfg": FuzzConfig(job="ECLK2", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C48:ECLK_0", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 50),
    },
    {
        "cfg": FuzzConfig(job="ECLK3", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C51:ECLK_3", "CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C48:ECLK_0"]),
        "rc": (55, 51),
    },
]

ignore_tiles = set([
    "CIB_R55C46:CIB"
    "CIB_R55C47:CIB",
    "CIB_R55C48:CIB",
    "CIB_R55C49:CIB",
    "CIB_R55C50:CIB",
    "CIB_R55C50:CIB",
    "CIB_R55C51:CIB",
    "CIB_R55C52:CIB",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("ECLK" in x)
        def pip_filter(x, nodes):
            src, snk = x
            return "PLL_CORE" not in src and "FBMUX_CORE" not in src and "FBMUX_CORE" not in snk \
                and "I217" not in snk and "I218" not in snk and "ECLKDDR" not in src \
                and "DQS_TOP" not in snk and "PADDI" not in src and "INCK_IOLOGIC" not in src
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
