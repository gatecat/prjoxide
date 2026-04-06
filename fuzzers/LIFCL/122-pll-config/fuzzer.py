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
    ("PLL_LLC",
        FuzzConfig(job="PLL_LL", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R29C1:GPLL_LLC_15K"]),
    ),
    ("PLL_LRC",
        FuzzConfig(job="PLL_LL", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R29C74:GPLL_LRC_15K"]),
    ),
]

def main(executor):
    for prim, cfg in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        if cfg.device == "LIFCL-40":
            cfg.sv = "pll.v"
        else:
            cfg.sv = "pll_17.v"

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
            desc="PLL_CORE primitive mode", executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.CLKMUX_FB".format(prim), ["CMUX_CLKOP", "CMUX_CLKOS", "CMUX_CLKOS2", "CMUX_CLKOS3", "CMUX_CLKOS4", "CMUX_CLKOS5"],
            lambda x: get_substs(mode="PLL_CORE", kv=("CLKMUX_FB", x)), False,
            desc="internal feedback selection", executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.LMMICLKMUX".format(prim), ["LMMICLK", "INV"],
            lambda x: get_substs(mode="PLL_CORE", kv=("LMMICLK", x), mux=True), False,
            desc="", executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.LMMIRESETNMUX".format(prim), ["LMMIRESETN", "INV"],
            lambda x: get_substs(mode="PLL_CORE", kv=("LMMIRESETN", x), mux=True), False,
            desc="", executor=executor)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
