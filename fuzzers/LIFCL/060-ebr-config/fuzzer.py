from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="EBRMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R29C26:MIB_EBR", "CIB_R29C27:EBR_1", "CIB_R29C28:EBR_2"])

# These config sets create a minimum bit change for mode fuzzing
defaults = {
    "NONE": "",
    "DP16K_MODE": "DP16K_MODE:::DATA_WIDTH_A=X18,DATA_WIDTH_B=X18,INIT_DATA=NO_INIT,WID=0b00000000000:CLKA=0,CLKB=0",
    "PDP16K_MODE": "PDP16K_MODE:::DATA_WIDTH_R=X36,DATA_WIDTH_W=X36,INIT_DATA=NO_INIT,WID=0b00000000000:CLKR=0,CLKW=0",
    "PDPSC16K_MODE": "PDPSC16K_MODE:::DATA_WIDTH_R=X36,DATA_WIDTH_W=X36,INIT_DATA=NO_INIT,WID=0b00000000000:CLK=0",
    "SP16K_MODE": "SP16K_MODE:::DATA_WIDTH=X18,INIT_DATA=NO_INIT,WID=0b00000000000:CLK=0",
    "FIFO16K_MODE": "FIFO16K_MODE:::FULLBITS=0b00000000000000,DATA_WIDTH_A=X36,DATA_WIDTH_B=X36 FIFO16K_MODE::::CKA=0,CKB=0"
}

ebr = "EBR0"

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
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(ebr), modes,
        lambda x: get_substs(x, default_cfg=True), False,
        desc="{} primitive mode".format(ebr))
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.DP16K_MODE.DATA_WIDTH_A".format(ebr), ["X1", "X2", "X4", "X9", "X18"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("DATA_WIDTH_A", x)), False,
        desc="data width of port A in DP16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.DP16K_MODE.DATA_WIDTH_B".format(ebr), ["X1", "X2", "X4", "X9", "X18"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("DATA_WIDTH_B", x)), False,
        desc="data width of port B in DP16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.PDP16K_MODE.DATA_WIDTH_W".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDP16K_MODE", kv=("DATA_WIDTH_W", x)), False,
        desc="data width of write port in PDP16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.PDP16K_MODE.DATA_WIDTH_R".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDP16K_MODE", kv=("DATA_WIDTH_R", x)), False,
        desc="data width of read port in PDP16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.PDPSC16K_MODE.DATA_WIDTH_W".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDPSC16K_MODE", kv=("DATA_WIDTH_W", x)), False,
        desc="data width of write port in PDPSC16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.PDPSC16K_MODE.DATA_WIDTH_R".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="PDPSC16K_MODE", kv=("DATA_WIDTH_R", x)), False,
        desc="data width of read port in PDPSC16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.SP16K_MODE.DATA_WIDTH".format(ebr), ["X1", "X2", "X4", "X9", "X18"],
        lambda x: get_substs(mode="SP16K_MODE", kv=("DATA_WIDTH", x)), False,
        desc="data width of R/W port in SP16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.FIFO16K_MODE.DATA_WIDTH_A".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="FIFO16K_MODE", kv=("DATA_WIDTH_A", x)), False,
        desc="data width of port A in FIFO16K_MODE")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.FIFO16K_MODE.DATA_WIDTH_B".format(ebr), ["X1", "X2", "X4", "X9", "X18", "X32", "X36"],
        lambda x: get_substs(mode="FIFO16K_MODE", kv=("DATA_WIDTH_B", x)), False,
        desc="data width of port B in FIFO16K_MODE")

    for mode, clksigs in [("DP16K_MODE", ["CLKA", "CLKB"]),
                            ("PDP16K_MODE", ["CLKW", "CLKR"]),
                            ("PDPSC16K_MODE", ["CLK"]),
                            ("SP16K_MODE", ["CLK"]),
                            ("FIFO16K_MODE", ["CKA", "CKB"])]:
        for sig in clksigs:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}.{}MUX".format(ebr, mode, sig), ["0", sig, "INV"],
                lambda x: get_substs(mode=mode, kv=(sig, x), mux=True), False,
                desc="clock inversion control for {}".format(sig))
    for mode, cwesigs in [("DP16K_MODE", ["WEA", "WEB", "CEA", "CEB", "RSTA", "RSTB"]),
                            ("PDP16K_MODE", ["WE", "CER", "CEW", "RST"]),
                            ("PDPSC16K_MODE", ["WE", "CER", "CEW", "RST"]),
                            ("SP16K_MODE", ["WE", "CE", "RST"]),
                            ("FIFO16K_MODE", ["CEA", "CEB", "RSTA", "RSTB"])]:
        for sig in cwesigs:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}.{}MUX".format(ebr, mode, sig), [sig, "INV"],
                lambda x: get_substs(mode=mode, kv=(sig, x), mux=True), False)

    for mode, outregs in [("DP16K_MODE", ["OUTREG_A", "OUTREG_B"]),
                            ("PDP16K_MODE", ["OUTREG"]),
                            ("PDPSC16K_MODE", ["OUTREG"]),
                            ("SP16K_MODE", ["OUTREG"]),
                            ("FIFO16K_MODE", ["OUTREG_A", "OUTREG_B"])]:
        for outreg in outregs:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}.{}".format(ebr, mode, outreg), ["USED", "BYPASSED"],
                lambda x: get_substs(mode=mode, kv=(outreg, x)), False,
                desc="extra output pipeline register enable/bypass")

    for mode, ports in [("DP16K_MODE", ["_A", "_B"]),
                            ("PDP16K_MODE", [""]),
                            ("PDPSC16K_MODE", [""]),
                            ("SP16K_MODE", [""]),
                            ("FIFO16K_MODE", ["_A", "_B"])]:
        for port in ports:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}.RESETMODE{}".format(ebr, mode, port), ["ASYNC", "SYNC"],
                lambda x: get_substs(mode=mode, kv=("RESETMODE{}".format(port), x)), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}.ASYNC_RST_RELEASE{}".format(ebr, mode, port), ["ASYNC", "SYNC"],
                lambda x: get_substs(mode=mode, kv=("ASYNC_RST_RELEASE{}".format(port), x)), False)

    for mode, csds in [("DP16K_MODE", ["CSDECODE_A", "CSDECODE_B"]),
                            ("PDP16K_MODE", ["CSDECODE_R", "CSDECODE_W"]),
                            ("PDPSC16K_MODE", ["CSDECODE_R", "CSDECODE_W"]),
                            ("SP16K_MODE", ["CSDECODE"]),]:
        for csd in csds:
            nonrouting.fuzz_word_setting(cfg, "{}.{}.{}".format(ebr, mode, csd), 3,
                lambda x: get_substs(mode=mode, kv=(csd, "".join(reversed(["1" if b else "0" for b in x])))),
                desc="port is enabled when CS inputs match this value".format(csd))

    nonrouting.fuzz_enum_setting(cfg, empty, "{}.GSR".format(ebr), ["ENABLED", "DISABLED"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("GSR", x)), False,
        desc="if `ENABLED`, then read ports are reset by user GSR")
    nonrouting.fuzz_enum_setting(cfg, empty, "{}.INIT_DATA".format(ebr), ["DYNAMIC", "STATIC", "NO_INIT"],
        lambda x: get_substs(mode="DP16K_MODE", kv=("INIT_DATA", x)), False,
        desc="selects initialisation mode")
    nonrouting.fuzz_word_setting(cfg, "{}.WID".format(ebr), 11,
        lambda x: get_substs(mode="DP16K_MODE", kv=("WID", "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
        desc="unique ID for the BRAM, used to initialise it in the bitstream")

    nonrouting.fuzz_word_setting(cfg, "{}.FIFO16K_MODE.FULLBITS".format(ebr), 14,
        lambda x: get_substs(mode="FIFO16K_MODE", kv=("FULLBITS", "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
        desc="FIFO 'full' threshold")
    nonrouting.fuzz_word_setting(cfg, "{}.FIFO16K_MODE.ALMOST_FULL".format(ebr), 14,
        lambda x: get_substs(mode="FIFO16K_MODE", kv=("ALMOST_FULL", "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
        desc="FIFO 'almost full' output threshold")
    nonrouting.fuzz_word_setting(cfg, "{}.FIFO16K_MODE.EMPTYBITS".format(ebr), 5,
        lambda x: get_substs(mode="EBR_CORE", kv=("EMPTY", "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
        desc="FIFO 'empty' threshold")
    nonrouting.fuzz_word_setting(cfg, "{}.FIFO16K_MODE.ALMOST_EMPTY".format(ebr), 14,
        lambda x: get_substs(mode="FIFO16K_MODE", kv=("ALMOST_EMPTY", "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
        desc="FIFO 'almost empty' output threshold")

if __name__ == "__main__":
    main()
