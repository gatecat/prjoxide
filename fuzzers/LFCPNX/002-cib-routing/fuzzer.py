from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    ((1, 18), FuzzConfig(job="CIBTROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R1C18:CIB_T"]), set(["TAP_CIBT_R1C14:TAP_CIBT"])),
    ((18, 1), FuzzConfig(job="CIBLRROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R18C1:CIB_LR"]), set(["TAP_PLC_R18C14:TAP_PLC"])),
    ((28, 17), FuzzConfig(job="CIBROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R28C17:CIB"]), set(["TAP_CIB_R28C14:TAP_CIB"])),
    ((28, 1), FuzzConfig(job="CIBLRAROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R28C1:CIB_LR_A"]), set(["TAP_CIB_R28C14:TAP_CIB"])),
]

def main():
    for rc, cfg, ignore in configs:
        cfg.setup()
        r, c = rc
        nodes = ["R{}C{}_J*".format(r, c)]
        extra_sources = []
        extra_sources += ["R{}C{}_H02E{:02}01".format(r, c+1, i) for i in range(8)]
        extra_sources += ["R{}C{}_H06E{:02}03".format(r, c+3, i) for i in range(4)]
        if r != 1:
            extra_sources += ["R{}C{}_V02N{:02}01".format(r-1, c, i) for i in range(8)]
            extra_sources += ["R{}C{}_V06N{:02}03".format(r-3, c, i) for i in range(4)]
        else:
            extra_sources += ["R{}C{}_V02N{:02}00".format(r, c, i) for i in range(8)]
            extra_sources += ["R{}C{}_V06N{:02}00".format(r, c, i) for i in range(4)]	
        extra_sources += ["R{}C{}_V02S{:02}01".format(r+1, c, i) for i in range(8)]	
        extra_sources += ["R{}C{}_V06S{:02}03".format(r+3, c, i) for i in range(4)]
        if c != 1:
            extra_sources += ["R{}C{}_H02W{:02}01".format(r, c-1, i) for i in range(8)]
            extra_sources += ["R{}C{}_H06W{:02}03".format(r, c-3, i) for i in range(4)]
        else:
            extra_sources += ["R{}C{}_H02W{:02}00".format(r, c, i) for i in range(8)]
            extra_sources += ["R{}C{}_H06W{:02}00".format(r, c, i) for i in range(4)]
        def pip_filter(pip, nodes):
            from_wire, to_wire = pip
            return not ("_CORE" in from_wire or "_CORE" in to_wire or "JCIBMUXOUT" in to_wire)
        def fc_filter(to_wire):
            return "CIBMUX" in to_wire or "CIBTEST" in to_wire or to_wire.startswith("R{}C{}_J".format(r, c))
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=True, bidir=True, ignore_tiles=ignore,
            pip_predicate=pip_filter, fc_filter=fc_filter)
        fuzz_interconnect(config=cfg, nodenames=extra_sources, regex=False, bidir=False, ignore_tiles=ignore,
            pip_predicate=pip_filter, fc_filter=fc_filter)

if __name__ == "__main__":
    main()
