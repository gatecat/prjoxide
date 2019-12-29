from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="DSPMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=[
    "CIB_R38C62:MIB_EBR", "CIB_R38C63:DSP_R_1", "CIB_R38C64:DSP_R_2",
    "CIB_R38C65:DSP_R_3", "CIB_R38C66:DSP_R_4", "CIB_R38C67:DSP_R_5",
    "CIB_R38C68:DSP_R_6", "CIB_R38C69:DSP_R_7", "CIB_R38C70:DSP_R_8",
    "CIB_R38C71:DSP_R_9", "CIB_R38C72:DSP_R_10", "CIB_R38C73:DSP_R_11",
])

defaults = {
    "NONE": "",
    "MULT9_CORE": "MULT9_CORE:::GSR=DISABLED:RSTA=0,CLK=0,CEA=0",
    "PREADD9_CORE": "PREADD9_CORE:::GSR=DISABLED,REGBYPSBL=REGISTER,REGBYPSBR0=REGISTER,REGBYPSBR1=REGISTER:RSTB=0,RSTCL=0,CLK=0,CEB=0,CECL=0",
    "MULT18_CORE": "MULT18_CORE:::MULT18X18=DISABLED,SFTEN=DISABLED,ROUNDBIT=ROUND_TO_BIT0",
    "MULT18X36_CORE": "MULT18X36_CORE:::MULT18X36=DISABLED,MULT36=DISABLED,SFTEN=DISABLED,ROUNDBIT=ROUND_TO_BIT0",
    "REG18_CORE": "REG18_CORE:::GSR=DISABLED:RSTP=0,CLK=0,CEP=0"
}

r = 37
c = 63

locs = [
    ("MULT18_0", "MULT18_CORE", "MULT18_CORE_R{}C{}".format(r, c)),
    ("MULT18_1", "MULT18_CORE", "MULT18_CORE_R{}C{}".format(r, c + 1)),
    ("MULT18_2", "MULT18_CORE", "MULT18_CORE_R{}C{}".format(r, c + 4)),
    ("MULT18_3", "MULT18_CORE", "MULT18_CORE_R{}C{}".format(r, c + 5)),

    ("REG18_L0_0", "REG18_CORE", "REG18_CORE_R{}C{}A".format(r, c + 2)),
    ("REG18_L0_1", "REG18_CORE", "REG18_CORE_R{}C{}B".format(r, c + 2)),
    ("REG18_L1_0", "REG18_CORE", "REG18_CORE_R{}C{}C".format(r, c + 2)),
    ("REG18_L1_1", "REG18_CORE", "REG18_CORE_R{}C{}D".format(r, c + 2)),

    ("REG18_H0_0", "REG18_CORE", "REG18_CORE_R{}C{}A".format(r, c + 6)),
    ("REG18_H0_1", "REG18_CORE", "REG18_CORE_R{}C{}B".format(r, c + 6)),
    ("REG18_H1_0", "REG18_CORE", "REG18_CORE_R{}C{}C".format(r, c + 6)),
    ("REG18_H1_1", "REG18_CORE", "REG18_CORE_R{}C{}D".format(r, c + 6)),

    ("MULT9_L0", "MULT9_CORE", "MULT9_CORE_R{}C{}A".format(r, c)),
    ("MULT9_H0", "MULT9_CORE", "MULT9_CORE_R{}C{}B".format(r, c)),
    ("MULT9_L1", "MULT9_CORE", "MULT9_CORE_R{}C{}A".format(r, c + 1)),
    ("MULT9_H1", "MULT9_CORE", "MULT9_CORE_R{}C{}B".format(r, c + 1)),
    ("MULT9_L2", "MULT9_CORE", "MULT9_CORE_R{}C{}A".format(r, c + 4)),
    ("MULT9_H2", "MULT9_CORE", "MULT9_CORE_R{}C{}B".format(r, c + 4)),
    ("MULT9_L3", "MULT9_CORE", "MULT9_CORE_R{}C{}A".format(r, c + 5)),
    ("MULT9_H3", "MULT9_CORE", "MULT9_CORE_R{}C{}B".format(r, c + 5)),

    ("PREADD9_L0", "PREADD9_CORE", "PREADD9_CORE_R{}C{}A".format(r, c)),
    ("PREADD9_H0", "PREADD9_CORE", "PREADD9_CORE_R{}C{}B".format(r, c)),
    ("PREADD9_L1", "PREADD9_CORE", "PREADD9_CORE_R{}C{}A".format(r, c + 1)),
    ("PREADD9_H1", "PREADD9_CORE", "PREADD9_CORE_R{}C{}B".format(r, c + 1)),
    ("PREADD9_L2", "PREADD9_CORE", "PREADD9_CORE_R{}C{}A".format(r, c + 4)),
    ("PREADD9_H2", "PREADD9_CORE", "PREADD9_CORE_R{}C{}B".format(r, c + 4)),
    ("PREADD9_L3", "PREADD9_CORE", "PREADD9_CORE_R{}C{}A".format(r, c + 5)),
    ("PREADD9_H3", "PREADD9_CORE", "PREADD9_CORE_R{}C{}B".format(r, c + 5)),
]

ce_sigs = {
    "MULT9_CORE": ["CEA", "CEP"],
    "PREADD9_CORE": ["CEB", "CECL"],
    "MULT18_CORE": [],
    "REG18_CORE": ["CEP"],
    "MULT18X36_CORE": []
}

rst_sigs = {
    "MULT9_CORE": ["RSTA", "RSTP"],
    "PREADD9_CORE": ["RSTB", "RSTCL"],
    "MULT18_CORE": [],
    "REG18_CORE": ["RSTP"],
    "MULT18X36_CORE": []
}

regs = {
    "MULT9_CORE": ["B", "A1", "A2"],
    "PREADD9_CORE": ["BR0", "BR1", "BL"],
    "MULT18_CORE": [],
    "REG18_CORE": [""],
    "MULT18X36_CORE": []
}

ed = ["ENABLED", "DISABLED"]
ub = ["USED", "BYPASS"]
rb = ["REGISTER", "BYPASS"]

misc_config = {
    "MULT9_CORE": [
        ("SIGNEDSTATIC_EN", ed, "`A` signedness from `SIGNEDSTATIC_EN` (when `ENABLED`) or `ASIGNED` input"),
        ("ASIGNED_OPERAND_EN", ed, "`A` is signed in `SIGNEDSTATIC_EN` mode"),
        ("BYPASS_MULT9", ub, "selects between actually doing 9x9 mult; or just passing through inputs"),
        ("SHIFTA", ed, "use shift register for `A`"),
        ("SR_18BITSHIFT_EN", ed, "use 18-bit shift register for `A`")
    ],
    "PREADD9_CORE": [
        ("SIGNEDSTATIC_EN", ed, "`B` and `C` signedness from parameters (`ENABLED`) or inputs"),
        ("SUBSTRACT_EN", ["SUBTRACTION", "ADDITION"], "preadder function"),
        ("CSIGNED", ed, "`C` signedness in `SIGNEDSTATIC_EN` mode"),
        ("BSIGNED_OPERAND_EN", ed, "`B` signedness in `SIGNEDSTATIC_EN` mode"),
        ("BYPASS_PREADD9", ub, "selects between pre-adder in datapath; or just passing through inputs"),
        ("SHIFTBR", rb, "use right shift register for `B`"),
        ("SHIFTBL", rb, "use left shift register for `B`"),
        ("PREADDCAS_EN", ed, "enable pre-adder carry cascade"),
        ("SR_18BITSHIFT_EN", ed, "use 18-bit shift register for `B`"),
        ("OPC", ["INPUT_B_AS_PREADDER_OPERAND", "INPUT_C_AS_PREADDER_OPERAND"], "selects 2nd pre-adder operand")
    ],
    "MULT18_CORE": [
        ("MULT18X18", ed, "enable 18x18 multiply"),
        ("SFTEN", ed, "enable variable shifter controlled by `SFTCTRL`"),
        ("ROUNDHALFUP", ed, ""),
        ("ROUNDRTZI", ["ROUND_TO_ZERO", "ROUND_TO_INFINITE"], "rounding mode"),
    ],
    "MULT18X36_CORE": [
        ("MULT18X36", ed, "enable 18x36 multiply"),
        ("MULT36", ed, "used as part of 36x36 multiply"),
        ("SFTEN", ed, "enable variable shifter controlled by `SFTCTRL`"),
        ("ROUNDHALFUP", ed, ""),
        ("MULT36X36H", ["USED_AS_LOWER_BIT_GENERATION", "USED_AS_HIGHER_BIT_GENERATION"], "half of 36x36 multiply selection"),
        ("ROUNDRTZI", ["ROUND_TO_ZERO", "ROUND_TO_INFINITE"], "rounding mode"),
    ],
    "REG18_CORE": [],
}

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "dsp.v"
    for dsp, prim, site in locs:
        def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False, extra_sigs=""):
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
                config = "{}::::{}={}{}".format(mode, kv[0], val, extra_sigs)
            else:
                config = "{}:::{}={}".format(mode, kv[0], kv[1])
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, prim=prim, site=site)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(dsp), ["NONE", prim],
            lambda x: get_substs(x, default_cfg=True), False, assume_zero_base=True,
            desc="{} primitive mode".format(dsp))
        if prim not in ("MULT18_CORE", "MULT18X36_CORE", "MULT36_CORE"):
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.GSR".format(dsp), ["ENABLED", "DISABLED"],
                        lambda x: get_substs(mode=prim, kv=("GSR", x)), False,
                        desc="if `ENABLED` primitive is reset by user GSR")
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.RESET".format(dsp), ["SYNC", "ASYNC"],
                        lambda x: get_substs(mode=prim, kv=("RESET", x)), False,
                        desc="selects synchronous or asynchronous reset for DSP registers")
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.CLKMUX".format(dsp), ["0", "CLK", "INV"],
                        lambda x: get_substs(mode=prim, kv=("CLK", x), mux=True),
                        False, assume_zero_base=True,
                        desc="clock gating and inversion control")
        for ce in ce_sigs[prim]:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}MUX".format(dsp, ce), ["1", ce, "INV"],
                    lambda x: get_substs(mode=prim, kv=(ce, x), mux=True, extra_sigs=",CLK=#SIG"),
                    False, assume_zero_base=True,
                    desc="{} gating and inversion control".format(ce))
        for rst in rst_sigs[prim]:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}MUX".format(dsp, rst), ["0", rst, "INV"],
                    lambda x: get_substs(mode=prim, kv=(rst, x), mux=True, extra_sigs=",CLK=#SIG"),
                    False, assume_zero_base=True,
                    desc="{} gating and inversion control".format(rst))
        for reg in regs[prim]:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.REGBYPS{}".format(dsp, reg), ["REGISTER", "BYPASS"],
                        lambda x: get_substs(mode=prim, kv=("REGBYPS{}".format(reg), x)), False, assume_zero_base=True,
                        desc="register enable or bypass{}{}".format(" for " if reg != "" else "", reg))
        for name, opts, desc in misc_config[prim]:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}".format(dsp, name), opts,
                        lambda x: get_substs(mode=prim, kv=(name, x)), False, assume_zero_base=True,
                        desc=desc)            
if __name__ == "__main__":
    main()
