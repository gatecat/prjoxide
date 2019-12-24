from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="IOROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C8:SYSIO_B5_0", "CIB_R56C9:SYSIO_B5_1"])

def main():
    cfg.setup()
    r = 56
    c = 8
    nodes = ["R{}C{}_*".format(r, c)]
    def nodename_filter(x, nodes):
        return ("R{}C{}_".format(r, c) in x) and ("_GEARING_PIC_TOP_" in x or "SEIO18_CORE" in x or "DIFFIO18_CORE" in x or "I217" in x or "I218" in x)
    def pip_filter(pip, nodes):
    	from_wire, to_wire = pip
    	return not ("ADC_CORE" in to_wire or "ECLKBANK_CORE" in to_wire or "MID_CORE" in to_wire or "REFMUX_CORE" in to_wire)
    fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True)

if __name__ == "__main__":
    main()
