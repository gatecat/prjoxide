from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

spine_cfgs = {
    ("CIB_R29C13:SPINE_L1", "R28C13"),
    ("CIB_R29C37:SPINE_L0", "R28C37"),
    ("CIB_R29C62:SPINE_R0", "R28C61"),
    ("CIB_R29C74:SPINE_R1", "R28C73"),
}

hrow_cfgs = {
    ("CIB_R29C37:SPINE_L0", "R28C31"),
    ("CIB_R29C62:SPINE_R0", "R28C61"),
}

trunk_cfgs = {
    ("CIB_R29C48:TRUNK_L_EBR_10", "R28C49_L"),
    ("CIB_R29C51:TRUNK_R", "R28C49_R"),
}

def main():
    for tile, rc in spine_cfgs:
        cfg = FuzzConfig(job="TAPROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}_VPSX{:02}00".format(rc, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)
    for tile, rc in hrow_cfgs:
        cfg = FuzzConfig(job="ROWROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}_HPRX{:02}00".format(rc, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)
    for tile, rcs in trunk_cfgs:
        cfg = FuzzConfig(job="TRUNKROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}HPRX{}".format(rcs, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)




if __name__ == "__main__":
    main()
