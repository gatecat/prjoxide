from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect

cr, cc = (37, 73)

configs = [
    ("HPFE", (37, 0), 12, "L",
        FuzzConfig(job="LMIDROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R37C0:LMID"])),
    ("HPFW", (37, 158), 12, "R",
        FuzzConfig(job="RMIDROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R37C159:RMID"])),
    ("VPFN", (73, 73), 18, "B",
        FuzzConfig(job="BMIDROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R74C73:BMID_0_ECLK_1", "CIB_R74C74:BMID_1_ECLK_2"])),
    ("VPFS", (0, 73), 16, "T",
        FuzzConfig(job="TMIDROUTE", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R0C73:TMID_0", "CIB_R0C74:TMID_1"])),
]

def main():
    for feed, rc, ndcc, side, cfg in configs:
        cfg.setup()
        r, c = rc
        nodes = []
        mux_nodes = []
        for i in range(ndcc):
            for j in range(4):
                nodes.append("R{}C{}_J{}{}_CMUX_CORE_CMUX{}".format(cr, cc, feed, i, j))
                nodes.append("R{}C{}_J{}{}_CMUX_CORE_CMUX{}".format(cr, cc, feed, i, j))
                nodes.append("R{}C{}_J{}{}_DCSMUX_CORE_DCSMUX{}".format(cr, cc, feed, i, j))
                nodes.append("R{}C{}_J{}{}_DCSMUX_CORE_DCSMUX{}".format(cr, cc, feed, i, j))
            nodes.append("R{}C{}_JCLKO_DCC_DCC{}".format(r, c, i))
            nodes.append("R{}C{}_JCE_DCC_DCC{}".format(r, c, i))
            nodes.append("R{}C{}_JCLKI_DCC_DCC{}".format(r, c, i))
            mux_nodes.append("R{}C{}_J{}{}_{}MID_CORE_{}MIDMUX".format(r, c, feed, i, side, side))
        for i in range(4):
            nodes.append("R{}C{}_JTESTINP{}_{}MID_CORE_{}MIDMUX".format(r, c, i, side, side))
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=False)
        fuzz_interconnect(config=cfg, nodenames=mux_nodes, regex=False, bidir=False, full_mux_style=True)
        def pip_filter(pip, nodes):
            from_wire, to_wire = pip
            return "PCLKT" in to_wire or "PCLKCIB" in to_wire
        fuzz_interconnect(config=cfg, nodenames=["R{}C{}_J*".format(r, c)], regex=True, bidir=False, full_mux_style=False,
            pip_predicate=pip_filter)

if __name__ == "__main__":
    main()
