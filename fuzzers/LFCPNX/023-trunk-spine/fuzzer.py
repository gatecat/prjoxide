from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

spine_cfgs = {
    ("CIB_R29C13:SPINE_UL2", "R19C13"),
    ("CIB_R29C37:SPINE_UL1", "R19C37"),
    ("CIB_R29C61:SPINE_UL0", "R19C61"),
    ("CIB_R29C86:SPINE_UR0", "R19C85"),
    ("CIB_R29C110:SPINE_UR1", "R19C109"),
    ("CIB_R29C134:SPINE_UR2", "R19C133"),
    ("CIB_R29C146:SPINE_UR3", "R19C145"),

    ("CIB_R47C13:SPINE_LL2", "R56C13"),
    ("CIB_R47C37:SPINE_LL1", "R56C37"),
    ("CIB_R47C61:SPINE_LL0", "R56C61"),
    ("CIB_R47C86:SPINE_LR0", "R56C85"),
    ("CIB_R47C110:SPINE_LR1", "R56C109"),
    ("CIB_R47C134:SPINE_LR2", "R56C133"),
    ("CIB_R47C146:SPINE_LR3", "R56C145"),

}

hrow_cfgs = {
    ("CIB_R29C61:SPINE_UL0", "R28C43"),
    ("CIB_R29C86:SPINE_UR0", "R28C109"),
    ("CIB_R47C61:SPINE_LL0", "R46C44"),
    ("CIB_R47C86:SPINE_LR0", "R46C109"),
}

trunk_cfgs = {
    ("CIB_R29C73:CMUX_4_TRUNK_UL", "R33C73_TL"),
    ("CIB_R29C74:CMUX_5_TRUNK_UR", "R33C73_TR"),
    ("CIB_R47C73:CMUX_2_TRUNK_LL", "R42C73_BL"),
    ("CIB_R47C74:CMUX_3_TRUNK_LR", "R42C73_BR"),
}

def main():
    for tile, rc in spine_cfgs:
        cfg = FuzzConfig(job="TAPROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}_VPSX{:02}00".format(rc, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)
    for tile, rc in hrow_cfgs:
        cfg = FuzzConfig(job="ROWROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}_HPRX{:02}00".format(rc, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)
    for tile, rcs in trunk_cfgs:
        cfg = FuzzConfig(job="TRUNKROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=[tile])
        cfg.setup()
        nodes = ["{}HPRX{}".format(rcs, i) for i in range(16)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)




if __name__ == "__main__":
    main()
