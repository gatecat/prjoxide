from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
from interconnect import fuzz_interconnect

cfgs = [
    ("PLL_LLC",
        FuzzConfig(job="PLL_LL", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R55C0:GPLL_LLC"]),
    ),
    ("PLL_ULC",
        FuzzConfig(job="PLL_LL", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C1:GPLL_ULC"]),
    ),
    ("PLL_LRC",
        FuzzConfig(job="PLL_LL", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R53C87:GPLL_LRC"]),
    ),
]
def main():
    for prim, cfg in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "pll.v"

        def bin_to_int(x):
            val = 0
            mul = 1
            for bit in x:
                if bit:
                    val |= mul
                mul *= 2
            return val

        def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False):
            if kv is None:
                config = ""
            elif mux:
                val = "#SIG"
                if kv[1] in ("0", "1"):
                    val = kv[1]
                if kv[1] == "INV":
                    val = "#INV"
                config = "{}::::{}={}".format(mode, kv[0], val)
            else:
                config = "{}:::{}={}".format(mode, kv[0], kv[1])
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=prim)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(prim), ["NONE", "PLL_CORE"],
            lambda x: get_substs(mode=x), False,
            desc="PLL_CORE primitive mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.LMMICLKMUX".format(prim), ["LMMICLK", "INV"],
            lambda x: get_substs(mode="PLL_CORE", kv=("LMMICLK", x), mux=True), False,
            desc="")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.LMMIRESETNMUX".format(prim), ["LMMIRESETN", "INV"],
            lambda x: get_substs(mode="PLL_CORE", kv=("LMMIRESETN", x), mux=True), False,
            desc="")

if __name__ == '__main__':
    main()
