from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="CLKRST", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C75:EFB_0", "CIB_R0C77:EFB_1_OSC", "CIB_R0C79:EFB_2", "CIB_R0C81:I2C_EFB_3"]),
        "rc": (0, 73),
        "keywords": ["CLKRST_CORE", "HSE_CORE", "MULTIBOOT_CORE", "LMMI_CORE", "CONFIG_IP_CORE"]
    },
    {
        "cfg": FuzzConfig(job="CLKRST", device="LIFCL-17", sv="../shared/route_17.v", tiles=["CIB_R0C66:EFB_15K", "CIB_R0C72:I2C_15K", "CIB_R0C71:OSC_15K", "CIB_R0C70:PMU_15K"]),
        "rc": (0, 52),
        "keywords": ["CLKRST_CORE", "CRE_CORE", "MULTIBOOT_CORE", "LMMI_CORE", "CONFIG_IP_CORE"]
    },
]

ignore_tiles = set([
    "CIB_R1C{}:CIB_T".format(c) for c in range(40, 87)
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        kws = config["keywords"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and any(kw in x for kw in kws)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
