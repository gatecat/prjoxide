from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    ([(11, 7), (11, 19)], [], FuzzConfig(job="TAPROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_PLC_R11C14:TAP_PLC"])),
    ([(10, 7), (10, 19)], [], FuzzConfig(job="TAPROUTECIB", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_CIB_R10C14:TAP_CIB"])),
    ([(1, 7), (1, 19)], [], FuzzConfig(job="TAPROUTECIBT", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_CIBT_R1C14:TAP_CIBT"])),
    ([(11, 80)], [], FuzzConfig(job="TAPROUTE_1S", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_PLC_1S_R11C74:TAP_PLC_1S"])),
    ([(10, 80)], [], FuzzConfig(job="TAPROUTECIB_1S", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_CIB_1S_R10C74:TAP_CIB_1S"])),
    ([(1, 80)], [], FuzzConfig(job="TAPROUTECIBT_1S", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_CIBT_1S_R1C74:TAP_CIBT_1S"])),

    ([(11, 7), ], [(11, 13), ], FuzzConfig(job="TAPROUTE_1SL", device="LIFCL-17", sv="../shared/route_17.v", tiles=["TAP_PLC_1S_L_R11C14:TAP_PLC_1S_L"])),
    ([(10, 7), ], [(10, 13), ], FuzzConfig(job="TAPROUTECIB_1SL", device="LIFCL-17", sv="../shared/route_17.v", tiles=["TAP_CIB_1S_L_R10C14:TAP_CIB_1S_L"])),
    ([(1, 7), ], [(1, 13), ], FuzzConfig(job="TAPROUTECIBT_1SL", device="LIFCL-17", sv="../shared/route_17.v", tiles=["TAP_CIBT_1S_L_R1C14:TAP_CIBT_1S_L"])),
]

def main():
    for locs, rlocs, cfg in configs:
        cfg.setup()
        nodes = []
        for r, c in locs:
            nodes += ["R{}C{}_HPBX{:02}00".format(r, c, i) for i in range(8)]
        for r, c in rlocs:
            nodes += ["R{}C{}_RHPBX{:02}00".format(r, c, i) for i in range(8)]
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=True)

if __name__ == "__main__":
    main()
