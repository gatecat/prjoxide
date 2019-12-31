from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
from interconnect import fuzz_interconnect

cfg = FuzzConfig(job="OSCMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C77:EFB_1_OSC"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "osc.v"

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
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.MODE", ["NONE", "OSC_CORE"],
        lambda x: get_substs(mode=x), False,
        desc="OSC_CORE primitive mode")
    nonrouting.fuzz_word_setting(cfg, "OSC_CORE.HF_CLK_DIV", 8,
        lambda x: get_substs(mode="OSC_CORE", kv=("HF_CLK_DIV", str(bin_to_int(x)))),
        desc="high frequency oscillator output divider")
    nonrouting.fuzz_word_setting(cfg, "OSC_CORE.HF_SED_SEC_DIV", 8,
        lambda x: get_substs(mode="OSC_CORE", kv=("HF_SED_SEC_DIV", str(bin_to_int(x)))),
        desc="high frequency oscillator output divider")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.DTR_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("DTR_EN", x)), False,
        desc="")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HF_FABRIC_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("HF_FABRIC_EN", x)), False,
        desc="enable HF oscillator trimming from input pins")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HF_OSC_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("HF_OSC_EN", x)), False,
        desc="enable HF oscillator")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HFDIV_FABRIC_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("HFDIV_FABRIC_EN", x)), False,
        desc="enable HF divider from parameter")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.LF_FABRIC_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("LF_FABRIC_EN", x)), False,
        desc="enable LF oscillator trimming from input pins")
    nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.LF_OUTPUT_EN", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="OSC_CORE", kv=("LF_OUTPUT_EN", x)), False,
        desc="enable LF oscillator output")

    # Fuzz oscillator routing
    cfg.sv = "../shared/route_40.v"
    nodes = ["R1C77_JLFCLKOUT_OSC_CORE", "R1C77_JHFCLKOUT_OSC_CORE",
        "R1C77_JHFSDCOUT_OSC_CORE", "R1C77_JHFCLKCFG_OSC_CORE",
        "R1C77_JHFOUTEN_OSC_CORE", "R1C77_JHFSDSCEN_OSC_CORE"]
    for i in range(9):
        nodes.append("R1C77_JHFTRMFAB{}_OSC_CORE".format(i))
        nodes.append("R1C77_JLFTRMFAB{}_OSC_CORE".format(i))
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=True, full_mux_style=False)

if __name__ == '__main__':
    main()
