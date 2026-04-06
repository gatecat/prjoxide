from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
from interconnect import fuzz_interconnect

cfg = FuzzConfig(job="GSR", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "gsr.v"

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
        return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config)
    nonrouting.fuzz_enum_setting(cfg, empty, "GSR_CORE.MODE", ["NONE", "GSR_CORE"],
        lambda x: get_substs(mode=x), False,
        desc="GSR_CORE primitive mode")

    nonrouting.fuzz_enum_setting(cfg, empty, "GSR_CORE.GSR", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="GSR_CORE", kv=("GSR", x)), False,
        desc="enable global set/reset")
    nonrouting.fuzz_enum_setting(cfg, empty, "GSR_CORE.GSR_SYNC", ["ASYNC", "SYNC"],
        lambda x: get_substs(mode="GSR_CORE", kv=("GSR_SYNC", x)), False,
        desc="synchronise global set/reset")

    nonrouting.fuzz_enum_setting(cfg, empty, "GSR_CORE.CLKMUX", ["CLK", "INV"],
        lambda x: get_substs(mode="GSR_CORE", kv=("CLK", x), mux=True), False,
        desc="")
    nonrouting.fuzz_enum_setting(cfg, empty, "GSR_CORE.GSR_NMUX", ["GSR_N", "INV"],
        lambda x: get_substs(mode="GSR_CORE", kv=("GSR_N", x), mux=True), False,
        desc="")
    # Fuzz GSR routing
    cfg.sv = "../shared/route_40.v"
    nodes = ["R28C49_JGSR_N_GSR_CORE_GSR_CENTER", "R28C49_JCLK_GSR_CORE_GSR_CENTER", "R28C49_JGSROUT_GSR_CORE_GSR_CENTER"]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=True, full_mux_style=False)

if __name__ == '__main__':
    fuzzloops.FuzzerMain(main)

