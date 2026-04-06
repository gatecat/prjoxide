import asyncio
import logging

from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ((37, 63), FuzzConfig(job="DSPMODER", device="LIFCL-40", sv="../shared/empty_40.v", tiles=[
        "CIB_R38C62:MIB_EBR", "CIB_R38C63:DSP_R_1", "CIB_R38C64:DSP_R_2",
        "CIB_R38C65:DSP_R_3", "CIB_R38C66:DSP_R_4", "CIB_R38C67:DSP_R_5",
        "CIB_R38C68:DSP_R_6", "CIB_R38C69:DSP_R_7", "CIB_R38C70:DSP_R_8",
        "CIB_R38C71:DSP_R_9", "CIB_R38C72:DSP_R_10", "CIB_R38C73:DSP_R_11"
    ])),
    ((37, 15), FuzzConfig(job="DSPMODEL", device="LIFCL-40", sv="../shared/empty_40.v", tiles=
        ["CIB_R38C13:MIB_EBR"] + ["CIB_R38C{}:DSP_L_{}".format(c + 14, c) for c in range(11)])),
]

defaults = {
    "NONE": "",
    "MULT9_CORE": "MULT9_CORE:::GSR=DISABLED:RSTA=0,CLK=0,CEA=0",
    "PREADD9_CORE": "PREADD9_CORE:::GSR=DISABLED,REGBYPSBL=REGISTER,REGBYPSBR0=REGISTER,REGBYPSBR1=REGISTER:RSTB=0,RSTCL=0,CLK=0,CEB=0,CECL=0",
    "MULT18_CORE": "MULT18_CORE:::MULT18X18=DISABLED,SFTEN=DISABLED,ROUNDBIT=ROUND_TO_BIT0",
    "MULT18X36_CORE": "MULT18X36_CORE:::MULT18X36=DISABLED,MULT36=DISABLED,SFTEN=DISABLED,ROUNDBIT=ROUND_TO_BIT0",
    "REG18_CORE": "REG18_CORE:::GSR=DISABLED:RSTP=0,CLK=0,CEP=0",
    "MULT36_CORE": "MULT36_CORE:::MULT36X36=DISABLED",
    "ACC54_CORE": "ACC54_CORE:::GSR=DISABLED,SIGN=DISABLED,STATICOPCODE_EN=DISABLED,OUTREGBYPS=REGISTER,CONSTSEL=BYPASS,\
ACCUMODE=MODE0,ACCUBYPS=USED,CREGBYPS1=REGISTER,CREGBYPS2=REGISTER,CREGBYPS3=REGISTER,\
CINREGBYPS1=REGISTER,CINREGBYPS2=REGISTER,CINREGBYPS3=REGISTER,LOADREGBYPS1=REGISTER,LOADREGBYPS2=REGISTER,LOADREGBYPS3=REGISTER,\
M9ADDSUBREGBYPS1=REGISTER,M9ADDSUBREGBYPS2=REGISTER,M9ADDSUBREGBYPS3=REGISTER,ADDSUBSIGNREGBYPS1=REGISTER,ADDSUBSIGNREGBYPS2=REGISTER,ADDSUBSIGNREGBYPS3=REGISTER,\
CASCOUTREGBYPS=REGISTER,SFTEN=DISABLED:RSTCIN=0,RSTO=0,RSTC=0,CLK=0,CECIN=0,CECTRL=0,CEO=0,CEC=0"

}

#r = 37
#c = 63

ce_sigs = {
    "MULT9_CORE": ["CEA", "CEP"],
    "PREADD9_CORE": ["CEB", "CECL"],
    "MULT18_CORE": [],
    "REG18_CORE": ["CEP"],
    "MULT18X36_CORE": [],
    "MULT36_CORE": [],
    "ACC54_CORE": ["CECIN", "CECTRL", "CEO", "CEC"],
}

rst_sigs = {
    "MULT9_CORE": ["RSTA", "RSTP"],
    "PREADD9_CORE": ["RSTB", "RSTCL"],
    "MULT18_CORE": [],
    "REG18_CORE": ["RSTP"],
    "MULT18X36_CORE": [],
    "MULT36_CORE": [],
    "ACC54_CORE": ["RSTCIN", "RSTCTRL", "RSTO", "RSTC"]
}

regs = {
    "MULT9_CORE": ["B", "A1", "A2"],
    "PREADD9_CORE": ["BR0", "BR1", "BL"],
    "MULT18_CORE": [],
    "REG18_CORE": [""],
    "MULT18X36_CORE": [],
    "MULT36_CORE": [],
    "ACC54_CORE": []
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
    "MULT36_CORE": [
        ("MULT36X36", ed, "enable 36x36 multiply")
    ],
    "ACC54_CORE": [
        ("SIGN", ed, "select dynamic signedness or signedness controlled by parameters"),
        ("M9ADDSUB_CTRL", ["ADDITION", "ADDSUB", "SUBADD", "SUBTRACTION"], "select stage 1 operation in static opcode mode"),
        ("ADDSUB_CTRL", ["ADD_ADD_CTRL_54_BIT_ADDER", "SUB_ADD_CTRL_54_BIT_ADDER", "ADD_SUB_CTRL_54_BIT_ADDER", "SUB_SUB_CTRL_54_BIT_ADDER"], "select stage 2 operation in static opcode mode"),
        ("STATICOPCODE_EN", ed, "operation controlled by input pins or parameters"),
        ("OUTREGBYPS", rb, "output register enable or bypass"),
        ("CONSTSEL", ["BYPASS", "SELECT"], "if `SELECT` then use PROGCONST for `C` operand"),
        ("DSPCASCADE", ed, "enable DSP cascading"),
        ("ACC108CASCADE", ["BYPASSCASCADE", "CASCADE2ACCU54TOFORMACCU108"], "cascade carry of two ACC54s to create a 108-bit accumulator"),
        ("ACCUBYPS", ub, "accumulator bypass"),
        ("CREGBYPS1", rb, "`C` register 1 enable or bypass"),
        ("CREGBYPS2", rb, "`C` register 2 enable or bypass"),
        ("CREGBYPS3", rb, "`C` register 3 enable or bypass"),
        ("CINREGBYPS1", rb, "`CIN` register 1 enable or bypass"),
        ("CINREGBYPS2", rb, "`CIN` register 2 enable or bypass"),
        ("CINREGBYPS3", rb, "`CIN` register 3 enable or bypass"),
        ("LOADREGBYPS1", rb, "`LOAD` register 1 enable or bypass"),
        ("LOADREGBYPS2", rb, "`LOAD` register 2 enable or bypass"),
        ("LOADREGBYPS3", rb, "`LOAD` register 3 enable or bypass"),
        ("M9ADDSUBREGBYPS1", rb, "`M9ADDSUB` register 1 enable or bypass"),
        ("M9ADDSUBREGBYPS2", rb, "`M9ADDSUB` register 2 enable or bypass"),
        ("M9ADDSUBREGBYPS3", rb, "`M9ADDSUB` register 3 enable or bypass"),
        ("ADDSUBSIGNREGBYPS1", rb, "`ADDSUBSIGN` register 1 enable or bypass"),
        ("ADDSUBSIGNREGBYPS2", rb, "`ADDSUBSIGN` register 2 enable or bypass"),
        ("ADDSUBSIGNREGBYPS3", rb, "`ADDSUBSIGN` register 3 enable or bypass"),
        ("ROUNDHALFUP", ed, ""),
        ("ROUNDRTZI", ["ROUND_TO_ZERO", "ROUND_TO_INFINITE"], "rounding mode"),
        ("CASCOUTREGBYPS", rb, "cascade output register enable or bypass"),
        ("SFTEN", ed, "enable variable shifter controlled by `SFTCTRL`"),
        ("ACCUMODE", ["MODE{}".format(i) for i in range(8)] , "accumulator mode"),
    ]
}

async def main(executor):
    async def per_config(x):
        rc, cfg = x
        r, c = rc
        locs = [
            ("ACC54_0", "ACC54_CORE", "ACC54_CORE_R{}C{}".format(r, c + 2)),
            ("ACC54_1", "ACC54_CORE", "ACC54_CORE_R{}C{}".format(r, c + 6)),

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

            ("MULT18X36_0", "MULT18X36_CORE", "MULT18X36_CORE_R{}C{}".format(r, c + 2)),
            ("MULT18X36_1", "MULT18X36_CORE", "MULT18X36_CORE_R{}C{}".format(r, c + 6)),

            ("MULT36", "MULT36_CORE", "MULT36_CORE_R{}C{}".format(r, c + 6)),
        ]
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "dsp.v"
        async def per_loc(l):
            dsp, prim, site = l
            def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False, extra_sigs=""):
                if default_cfg:
                    config = defaults[mode] + extra_sigs
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

            futures = []
            def fuzz_enum_setting(*args, **kwargs):
                futures.append(asyncio.wrap_future(executor.submit(nonrouting.fuzz_enum_setting, cfg, empty, *args, **kwargs, executor=executor)))


            if prim == "ACC54_CORE":
                # Use 'cover' to get a minimal bit set
                fuzz_enum_setting("{}.MODE".format(dsp), ["NONE", prim],
                        lambda x: get_substs(x[0], default_cfg=True, extra_sigs=x[1]), False, assume_zero_base=True,
                        min_cover={"NONE": [""], "ACC54_CORE": [" ACC54_CORE::::RSTCTRL=0", " ACC54_CORE::::RSTCTRL=#SIG"]},
                        desc="{} primitive mode".format(dsp))
            else:
                fuzz_enum_setting("{}.MODE".format(dsp), ["NONE", prim],
                    lambda x: get_substs(x, default_cfg=True), False, assume_zero_base=True,
                    desc="{} primitive mode".format(dsp))
            if prim not in ("MULT18_CORE", "MULT18X36_CORE", "MULT36_CORE"):
                fuzz_enum_setting("{}.GSR".format(dsp), ["ENABLED", "DISABLED"],
                            lambda x: get_substs(mode=prim, kv=("GSR", x)), False,
                            desc="if `ENABLED` primitive is reset by user GSR")
                fuzz_enum_setting("{}.RESET".format(dsp), ["SYNC", "ASYNC"],
                            lambda x: get_substs(mode=prim, kv=("RESET", x)), False,
                            desc="selects synchronous or asynchronous reset for DSP registers")
                fuzz_enum_setting("{}.CLKMUX".format(dsp), ["0", "CLK", "INV"],
                            lambda x: get_substs(mode=prim, kv=("CLK", x), mux=True),
                            False, assume_zero_base=True,
                            desc="clock gating and inversion control")
            for ce in ce_sigs[prim]:
                fuzz_enum_setting("{}.{}MUX".format(dsp, ce), ["1", ce, "INV"],
                        lambda x,ce=ce: get_substs(mode=prim, kv=(ce, x), mux=True, extra_sigs=",CLK=#SIG"),
                        False, assume_zero_base=True,
                        desc="{} gating and inversion control".format(ce))
            for rst in rst_sigs[prim]:
                fuzz_enum_setting("{}.{}MUX".format(dsp, rst), ["0", rst, "INV"],
                        lambda x,rst=rst: get_substs(mode=prim, kv=(rst, x), mux=True, extra_sigs=",CLK=#SIG"),
                        False, assume_zero_base=True,
                        desc="{} gating and inversion control".format(rst))
            for reg in regs[prim]:
                fuzz_enum_setting("{}.REGBYPS{}".format(dsp, reg), ["REGISTER", "BYPASS"],
                            lambda x,reg=reg: get_substs(mode=prim, kv=("REGBYPS{}".format(reg), x)), False, assume_zero_base=True,
                            desc="register enable or bypass{}{}".format(" for " if reg != "" else "", reg))
            for name, opts, desc in misc_config[prim]:
                fuzz_enum_setting("{}.{}".format(dsp, name), opts,
                            lambda x,desc=desc,name=name: get_substs(mode=prim, kv=(name, x)), False, assume_zero_base=True,
                            desc=desc)

            await asyncio.gather(*futures)
        await asyncio.gather(*[per_loc(l) for l in locs])
    await asyncio.gather(*[per_config(config) for config in configs])

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(main)


