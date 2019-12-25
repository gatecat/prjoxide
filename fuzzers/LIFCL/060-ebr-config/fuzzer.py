from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="EBRMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R29C26:MIB_EBR", "CIB_R29C27:EBR_1", "CIB_R29C28:EBR_2"])

# These config sets create a minimum bit change for mode fuzzing
defaults = {
    "NONE": "",
    "DP16K_MODE": "DP16K_MODE:::DATA_WIDTH_A=NONE,DATA_WIDTH_B=NONE,INIT_DATA=NO_INIT,WID=0b00000000000:CLKA=#OFF,CLKB=#OFF",
    "PDP16K_MODE": "PDP16K_MODE:::DATA_WIDTH_R=NONE,DATA_WIDTH_W=NONE,INIT_DATA=NO_INIT,WID=0b00000000000:CLKR=#OFF,CLKW=#OFF",
    "PDPSC16K_MODE": "PDPSC16K_MODE:::DATA_WIDTH_A=NONE,DATA_WIDTH_B=NONE,INIT_DATA=NO_INIT,WID=0b00000000000:CLK=#OFF",
    "SP16K_MODE": "SP16K_MODE:::DATA_WIDTH=NONE,INIT_DATA=NO_INIT,WID=0b00000000000:CLK=#OFF",
    "FIFO16K_MODE": "FIFO16K_MODE:::FULLBITS=0b00000000000000,DATA_WIDTH_A=NONE,DATA_WIDTH_B=NONE FIFO16K_MODE::::CKA=0,CKB=0"
}

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "ebr.v"

    def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False):
        if default_cfg:
            config = defaults[mode]
        elif kv is None:
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
    modes = ["NONE", "DP16K_MODE", "PDP16K_MODE", "PDPSC16K_MODE", "SP16K_MODE", "FIFO16K_MODE"]
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.MODE", modes,
        lambda x: get_substs(x, default_cfg=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.DATA_WIDTH_A", ["X1", "X2", "X4", "X9", "X18"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("DATA_WIDTH_A", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.DATA_WIDTH_B", ["X1", "X2", "X4", "X9", "X18"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("DATA_WIDTH_B", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.PDP16K_MODE.DATA_WIDTH_W", ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDP16K_MODE", kv=("DATA_WIDTH_W", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.PDP16K_MODE.DATA_WIDTH_R", ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDP16K_MODE", kv=("DATA_WIDTH_R", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.CLKAMUX", ["0", "CLKA", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("CLKA", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.CLKBMUX", ["0", "CLKB", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("CLKB", x), mux=True), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.WEAMUX", ["WEA", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("WEA", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.WEBMUX", ["WEB", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("WEB", x), mux=True), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.CEAMUX", ["CEA", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("CEA", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.CEBMUX", ["CEB", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("CEB", x), mux=True), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.RSTMUX", ["RST", "INV"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("RST", x), mux=True), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.OUTREG_A", ["USED", "BYPASSED"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("OUTREG_A", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.DP16K_MODE.OUTREG_B", ["USED", "BYPASSED"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("OUTREG_B", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "EBR0.GSR", ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("GSR", x)), False)
    nonrouting.fuzz_word_setting(cfg, "EBR0.WID", 11,
        lambda x: get_substs(mode="DP16K_MODE", kv=("WID", "0b" + "".join(reversed(["1" if b else "0" for b in x])))))
if __name__ == "__main__":
    main()
