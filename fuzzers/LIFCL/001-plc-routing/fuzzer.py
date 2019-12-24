from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="PLCROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["R16C22:PLC"])

def main():
    cfg.setup()
    r = 16
    c = 22
    nodes = ["R{}C{}_J*".format(r, c)]
    extra_sources = []
    extra_sources += ["R{}C{}_H02E{:02}01".format(r, c+1, i) for i in range(8)]
    extra_sources += ["R{}C{}_H06E{:02}03".format(r, c+3, i) for i in range(4)]
    extra_sources += ["R{}C{}_V02N{:02}01".format(r-1, c, i) for i in range(8)]	
    extra_sources += ["R{}C{}_V06N{:02}03".format(r-3, c, i) for i in range(4)]	
    extra_sources += ["R{}C{}_V02S{:02}01".format(r+1, c, i) for i in range(8)]	
    extra_sources += ["R{}C{}_V06S{:02}03".format(r+3, c, i) for i in range(4)]	
    extra_sources += ["R{}C{}_H02W{:02}01".format(r, c-1, i) for i in range(8)]
    extra_sources += ["R{}C{}_H06W{:02}03".format(r, c-3, i) for i in range(4)]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=True, bidir=True, ignore_tiles=set(["TAP_PLC_R16C14:TAP_PLC"]))
    fuzz_interconnect(config=cfg, nodenames=extra_sources, regex=False, bidir=False, ignore_tiles=set(["TAP_PLC_R16C14:TAP_PLC"]))

if __name__ == "__main__":
    main()
