from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="DSPROUTE0", device="LIFCL-40", sv="../shared/route_40.v", tiles=[
                "CIB_R38C63:DSP_R_1", "CIB_R38C62:MIB_EBR", "CIB_R38C64:DSP_R_2",
                "CIB_R38C65:DSP_R_3", "CIB_R38C66:DSP_R_4", "CIB_R38C67:DSP_R_5",
                "CIB_R38C68:DSP_R_6", "CIB_R38C69:DSP_R_7", "CIB_R38C70:DSP_R_8",
                "CIB_R38C71:DSP_R_9", "CIB_R38C72:DSP_R_10", "CIB_R38C73:DSP_R_11",
            ]),
        "rc": (37, 63),
    },
    {
        "cfg": FuzzConfig(job="DSPROUTE1", device="LIFCL-40", sv="../shared/route_40.v", tiles=[
                "CIB_R38C14:DSP_L_0", "CIB_R38C13:MIB_EBR", "CIB_R38C15:DSP_L_1",
                "CIB_R38C16:DSP_L_2", "CIB_R38C17:DSP_L_3", "CIB_R38C18:DSP_L_4",
                "CIB_R38C19:DSP_L_5", "CIB_R38C20:DSP_L_6", "CIB_R38C21:DSP_L_7",
                "CIB_R38C22:DSP_L_8", "CIB_R38C23:DSP_L_9", "CIB_R38C24:DSP_L_10",
            ]),
        "rc": (37, 14),
    },
]

ignore_tiles = set(
    ["CIB_R37C{}:CIB".format(c) for c in range(61, 75)] + 
    ["CIB_R37C{}:CIB".format(c) for c in range(10, 29)]
)

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        for c2 in range(c, c + 11):

            # Put fixed connections in the most suitable tile
            permuted_tiles = []
            for tile in cfg.tiles:
                if "C{}:".format(c2) in tile:
                    permuted_tiles.append(tile)
            for tile in cfg.tiles:
                if tile not in permuted_tiles:
                    permuted_tiles.append(tile)
            cfg.tiles = permuted_tiles

            nodes = ["R{}C{}_*".format(r, c2)]
            def nodename_filter(x, nodes):
                return ("R{}C{}_".format(r, c2) in x) and ("MULT9_CORE" in x or "PREADD9_CORE" in x or "MULT18_CORE" in x or "MULT18X36_CORE" in x or "REG18_CORE" in x or "MULT36_CORE" in x or "ACC54_CORE" in x)
            fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
