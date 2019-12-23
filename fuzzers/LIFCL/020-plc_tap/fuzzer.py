from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="TAPROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["TAP_PLC_R11C14:TAP_PLC"])

def main():
    cfg.setup()
    nodes = ["R11C7_HPBX{:02}00".format(i) for i in range(8)] + ["R11C19_HPBX{:02}00".format(i) for i in range(8)]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=True)

if __name__ == "__main__":
    main()
