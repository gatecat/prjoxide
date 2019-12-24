from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="IOROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C8:SYSIO_B5_0", "CIB_R56C9:SYSIO_B5_1"])

def main():
    cfg.setup()
    r = 56
    c = 8
    nodes = ["R{}C{}_*".format(r, c)]
    def nodename_filter(x):
        return "_GEARING_PIC_TOP_" in x or "SEIO18_CORE" in x or "DIFFIO18_CORE" in x or "I217" in x or "I218" in x
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=True, bidir=True)

if __name__ == "__main__":
    main()
