from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="PLCROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["R16C22:PLC"])

def main():
    cfg.setup()
    r = 16
    c = 22
    nodes = ["R{}C{}_J*".format(r, c)]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=True, bidir=True)

if __name__ == "__main__":
    main()
