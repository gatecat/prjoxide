from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect

cr, cc = (28, 49)

configs = [
    ("HPFE", (28, 0), 12, "L",
        FuzzConfig(job="LMIDROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R28C0:LMID"])),
    ("HPFW", (28, 86), 12, "R",
        FuzzConfig(job="RMIDROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R28C87:RMID_DLY20"])),
    ("VPFN", (56, 49), 18, "B",
        FuzzConfig(job="BMIDROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C50:BMID_1_ECLK_2"])),
    ("VPFS", (0, 49), 16, "T",
        FuzzConfig(job="TMIDROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R0C49:TMID_0", "CIB_R0C50:TMID_1"])),

]

def main():
    for feed, rc, ndcc, side, cfg in configs:
        cfg.setup()
        r, c = rc
        nodes = []
        mux_nodes = []
        for i in range(ndcc):
            for j in range(2):
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
