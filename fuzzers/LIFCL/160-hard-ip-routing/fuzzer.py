from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="DPHYROUTE0", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C4:MIPI_DPHY_0", "CIB_R0C2:DPHY_CLKMUX0"]),
        "rc": (0, 2),
    },
    {
        "cfg": FuzzConfig(job="DPHYROUTE1", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C28:MIPI_DPHY_1", "CIB_R0C26:DPHY_CLKMUX1"]),
        "rc": (0, 26),
    },
    {
        "cfg": FuzzConfig(job="PCIEROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C57:PCIE_X1"]),
        "rc": (0, 57),
    },
    {
        "cfg": FuzzConfig(job="ADCROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R50C87:ADC"]),
        "rc": (50, 86),
    },
]

ignore_tiles = set(
    ["CIB_R1C{}:CIB_T".format(c) for c in range(1, 86)] + 
    ["CIB_R{}C1:CIB_LR".format(r) for r in range(2, 54)] +
    ["CIB_R{}C86:CIB_LR".format(r) for r in range(2, 54)] +
    ["CIB_R46C86:CIB_LR_A", "CIB_R46C1:CIB_LR_A"]
)

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("DPHY_CORE" in x or "DPHY_REFCLOCK_MUX_CORE" in x or "PCIE_CORE" in x or "ADC_CORE" in x)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
