from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="REGCFG", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["R2C2:PLC"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "ff.v"

    def per_slice(slicen):
        for r in range(2):
            def get_substs(regset="SET", sel="DL", lsrmode="LSR", srmode="LSR_OVER_CE", gsr="DISABLED", mux="", used="", arc=""):
                return dict(z=slicen, k=str(r), mux=mux, regset=regset,
                            sel=sel, lsrmode=lsrmode, srmode=srmode, gsr=gsr, used=used, arc=arc, q_used_comment="//" if used == "" else "" )
            def get_used_substs(used):
                u = ""
                arc = ""
                if used == "YES":
                    u = ", .Q{}(q) ".format(r)
                    arc = "R2C2_JQ{}.R2C2_JQ{}_SLICE{}".format(str(("ABCD".index(slicen)*2)+r), r, slicen)
                return get_substs(used=u, arc=arc)
            def get_ddr_substs(ddr):
                return get_substs(mux="REGDDR:{}".format(ddr))
            def get_clkmux_substs(mux):
                if mux == "CLK":
                    cm = "CLK:::CLK=#SIG"
                elif mux == "INV":
                    cm = "CLK:::CLK=#INV"
                elif mux == "1":
                    cm = "CONST:::CONST=1"
                elif mux == "0":
                    cm = "#OFF"
                elif mux == "DDR":
                    return get_substs(mux="REGDDR:ENABLED")
                return get_substs(mux="CLKMUX:{}".format(cm))
            def get_cemux_substs(mux):
                if mux == "CE":
                    cm = "CE:::CE=#SIG"
                elif mux == "INV":
                    cm = "CE:::CE=#INV"
                return get_substs(mux="CEMUX:{}".format(cm))
            def get_lsrmux_substs(mux):
                if mux == "LSR":
                    cm = "LSR:::CE=#SIG"
                elif mux == "INV":
                    cm = "LSR:::LSR=#INV"
                elif mux == "0":
                    cm = "CONST:::CONST=0"
                return get_substs(mux="LSRMUX:{}".format(cm))
            nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.REG{}.USED".format(slicen, r), ["YES", "NO"],
                lambda x: get_used_substs(x), False,
                desc="`YES` if SLICE {} register {} (Q{}) is used".format(slicen, r, r))
            nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.REG{}.REGSET".format(slicen, r), ["RESET", "SET"],
                lambda x: get_substs(regset=x), True,
                desc="SLICE {} register {} set/reset and init value".format(slicen, r))
            nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.REG{}.SEL".format(slicen, r), ["DL", "DF"],
                lambda x: get_substs(sel=x), True,
                desc="SLICE {} register {} data selection. `DL`=LUT output, `DF`=bypass (M{})".format(slicen, r, r))
            nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.REG{}.LSRMODE".format(slicen, r), ["LSR", "PRLD"],
                lambda x: get_substs(lsrmode=x), True)
        h = "A/B" if slicen in ("A", "B") else "C/D"
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.GSR".format(slicen, r), ["ENABLED", "DISABLED"],
            lambda x: get_substs(gsr=x), False,
            desc="if `ENABLED`, then FFs in SLICE {} are set/reset by user GSR signal".format(h))
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.SRMODE".format(slicen, r), ["ASYNC", "LSR_OVER_CE"],
            lambda x: get_substs(srmode=x), False,
            desc="selects asynchronous set/reset, or sync set/reset which overrides CE for FFs in SLICE {}".format(h))
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.REGDDR".format(slicen, r), ["ENABLED", "DISABLED"],
            lambda x: get_ddr_substs(x), False,
            desc="if ENABLED then FFs in SLICE {} are clocked by both edges of the clock".format(h))
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.CLKMUX".format(slicen, r), ["CLK", "INV", "0", "DDR"],
            lambda x: get_clkmux_substs(x), False,
            desc="selects clock polarity")
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.CEMUX".format(slicen, r), ["CE", "INV"],
            lambda x: get_cemux_substs(x), False,
            desc="selects clock enable polarity")
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.LSRMUX".format(slicen, r), ["LSR", "INV", "0"],
            lambda x: get_lsrmux_substs(x), False,
            desc="selects set/reset gating and inversion")
    fuzzloops.parallel_foreach(["A", "B", "C", "D"], per_slice)

if __name__ == "__main__":
    main()
