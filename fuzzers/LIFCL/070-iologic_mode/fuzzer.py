from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ("IOL_B8A", "IOLOGICA", FuzzConfig(job="IOL5AMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C8:SYSIO_B5_0", "CIB_R56C9:SYSIO_B5_1"])),
    ("IOL_B8B", "IOLOGICB", FuzzConfig(job="IOL5BMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C8:SYSIO_B5_0", "CIB_R56C9:SYSIO_B5_1"])),
    ("IOL_B18A", "IOLOGICA", FuzzConfig(job="IOL4AMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C18:SYSIO_B4_0", "CIB_R56C19:SYSIO_B4_1"])),
    ("IOL_B18B", "IOLOGICB", FuzzConfig(job="IOL4BMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C18:SYSIO_B4_0", "CIB_R56C19:SYSIO_B4_1"])),
    ("IOL_B56A", "IOLOGICA", FuzzConfig(job="IOL3AMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C56:SYSIO_B3_0", "CIB_R56C57:SYSIO_B3_1"])),
    ("IOL_B56B", "IOLOGICB", FuzzConfig(job="IOL3BMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C56:SYSIO_B3_0", "CIB_R56C57:SYSIO_B3_1"])),

    ("IOL_R32A", "SIOLOGICA", FuzzConfig(job="IOL2AEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R32C87:SYSIO_B2_0_EVEN"])),
    ("IOL_R32B", "SIOLOGICB", FuzzConfig(job="IOL2BEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R32C87:SYSIO_B2_0_EVEN"])),
    ("IOL_L32A", "SIOLOGICA", FuzzConfig(job="IOL6AEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R32C0:SYSIO_B6_0_EVEN"])),
    ("IOL_L32B", "SIOLOGICB", FuzzConfig(job="IOL6BEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R32C0:SYSIO_B6_0_EVEN"])),
    ("IOL_R13A", "SIOLOGICA", FuzzConfig(job="IOL1AEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R13C87:SYSIO_B1_0_EVEN"])),
    ("IOL_R13B", "SIOLOGICB", FuzzConfig(job="IOL1BEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R13C87:SYSIO_B1_0_EVEN"])),
    ("IOL_L6A", "SIOLOGICA", FuzzConfig(job="IOL7AEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C0:SYSIO_B7_0_EVEN"])),
    ("IOL_L6B", "SIOLOGICB", FuzzConfig(job="IOL7BEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C0:SYSIO_B7_0_EVEN"])),

    ("IOL_R34A", "SIOLOGICA", FuzzConfig(job="IOL2AOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R34C87:SYSIO_B2_0_ODD"])),
    ("IOL_R34B", "SIOLOGICB", FuzzConfig(job="IOL2BOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R34C87:SYSIO_B2_0_ODD"])),
    ("IOL_L34A", "SIOLOGICA", FuzzConfig(job="IOL6AOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R34C0:SYSIO_B6_0_ODD"])),
    ("IOL_L34B", "SIOLOGICB", FuzzConfig(job="IOL6BOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R34C0:SYSIO_B6_0_ODD"])),
    ("IOL_R15A", "SIOLOGICA", FuzzConfig(job="IOL1AOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R15C87:SYSIO_B1_0_ODD"])),
    ("IOL_R15B", "SIOLOGICB", FuzzConfig(job="IOL1BOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R15C87:SYSIO_B1_0_ODD"])),
    ("IOL_L8A", "SIOLOGICA", FuzzConfig(job="IOL7AOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R8C0:SYSIO_B7_0_ODD"])),
    ("IOL_L8B", "SIOLOGICB", FuzzConfig(job="IOL7BOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R8C0:SYSIO_B7_0_ODD"])),

    ("IOL_T76A", "SIOLOGICA", FuzzConfig(job="IOL0AOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C76:SYSIO_B0_0_ODD"])),
    ("IOL_T76B", "SIOLOGICB", FuzzConfig(job="IOL0BOMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C76:SYSIO_B0_0_ODD"])),

    ("IOL_T78A", "SIOLOGICA", FuzzConfig(job="IOL0AEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C78:SYSIO_B0_0_EVEN"])),
    ("IOL_T78B", "SIOLOGICB", FuzzConfig(job="IOL0BEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C78:SYSIO_B0_0_EVEN"])),

    ("IOL_R46A", "SIOLOGICA", FuzzConfig(job="IOL2CMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C87:SYSIO_B2_0_C", "CIB_R47C87:SYSIO_B2_0_REM"])),
    ("IOL_R46B", "SIOLOGICB", FuzzConfig(job="IOL2DMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C87:SYSIO_B2_0_C", "CIB_R47C87:SYSIO_B2_0_REM"])),
    ("IOL_L46A", "SIOLOGICA", FuzzConfig(job="IOL6CMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C0:SYSIO_B6_0_C", "CIB_R47C0:SYSIO_B6_0_REM"])),
    ("IOL_L46B", "SIOLOGICB", FuzzConfig(job="IOL6DMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C0:SYSIO_B6_0_C", "CIB_R47C0:SYSIO_B6_0_REM"])),
    ("IOL_R10A", "SIOLOGICA", FuzzConfig(job="IOL1CMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C87:SYSIO_B1_0_C", "CIB_R11C87:SYSIO_B1_0_REM"])),
    ("IOL_R10B", "SIOLOGICB", FuzzConfig(job="IOL1DMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C87:SYSIO_B1_0_C", "CIB_R11C87:SYSIO_B1_0_REM"])),
    ("IOL_L10A", "SIOLOGICA", FuzzConfig(job="IOL7CMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C0:SYSIO_B7_0_C", "CIB_R11C0:SYSIO_B7_0_REM"])),
    ("IOL_L10B", "SIOLOGICB", FuzzConfig(job="IOL7DMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C0:SYSIO_B7_0_C", "CIB_R11C0:SYSIO_B7_0_REM"])),
]

def main():
    def per_config(x):
        site, prim, cfg = x
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "iologic.v"
        s = (prim[0] == "S")

        def get_substs(mode="NONE", default_cfg=False, scope=None, kv=None, mux=False, glb=False, dqs=False):
            if default_cfg:
                config = "SCLKINMUX:#OFF GSR:ENABLED INMUX:#OFF OUTMUX:#OFF DELAYMUX:#OFF SRMODE:#ASYNC LOAD_NMUX:#OFF DIRMUX:#OFF MOVEMUX:#OFF CEOUTMUX:#OFF CEINMUX:#OFF LSRINMUX:#OFF LSROUTMUX:#OFF STOP_EN:DISABLED"
            elif kv is None:
                config = ""
            elif glb:
                config="{}:{}".format(kv[0], kv[1])
            elif dqs and "_" in kv[1]:
                val, dqsmode = kv[1].split("_")
                config = "{}:::{}={} WRCLKMUX:{}".format(mode if scope is None else scope, kv[0], val, dqsmode)
            elif mux:
                signame = kv[0].replace("MUX", "")
                val = "{}:::{}=#SIG".format(signame, signame)
                if kv[1] in ("0", "1"):
                    val = "CONST:::CONST={}".format(kv[1])
                if kv[1] == "INV":
                    val = "{}:::{}=#INV".format(signame, signame)
                config = "{}:{}".format(kv[0], val)
            else:
                config = "{}:::{}={}".format(mode if scope is None else scope, kv[0], kv[1])
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site, s="S" if s else "")
        modes = ["NONE", "IREG_OREG", "IDDRX1_ODDRX1"]
        if not s:
            modes += ["IDDRXN", "ODDRXN", "MIDDRXN_MODDRXN"]
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(prim), modes,
            lambda x: get_substs(x, default_cfg=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.GSR".format(prim), ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="IREG_OREG", kv=("GSR", x), glb=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.SRMODE".format(prim), ["ASYNC", "LSR_OVER_CE"],
            lambda x: get_substs(mode="IREG_OREG", kv=("SRMODE", x), glb=True), False)
        if not s:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.IDDRXN.DDRMODE".format(prim), ["NONE", "IDDRX2", "IDDR71", "IDDRX4", "IDDRX5"],
                lambda x: get_substs(mode="IDDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x)), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.ODDRXN.DDRMODE".format(prim), ["NONE", "ODDRX2", "ODDR71", "ODDRX4", "ODDRX5"],
                lambda x: get_substs(mode="ODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x)), False)

        for sig in ("SCLKIN", "SCLKOUT", "CEIN", "CEOUT", "LSRIN", "LSROUT"):
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}MUX".format(prim, sig), ["1" if sig[0:2] == "CE" else "0", sig, "INV"],
                lambda x: get_substs(mode="IREG_OREG", kv=("{}MUX".format(sig), x), mux=True), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "{}.INMUX".format(prim), ["BYPASS", "DELAY"],
            lambda x: get_substs(mode="IREG_OREG", kv=("INMUX", x), glb=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.OUTMUX".format(prim), ["BYPASS", "DELAY"],
            lambda x: get_substs(mode="IREG_OREG", kv=("OUTMUX", x), glb=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.DELAYMUX".format(prim), ["OUT_REG", "IN"],
            lambda x: get_substs(mode="IREG_OREG", kv=("DELAYMUX", x), glb=True), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "{}.MOVEMUX".format(prim), ["0", "MOVE"],
            lambda x: get_substs(mode="IREG_OREG", kv=("MOVEMUX", x), glb=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.DIRMUX".format(prim), ["0", "DIR"],
            lambda x: get_substs(mode="IREG_OREG", kv=("DIRMUX", x), glb=True), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.LOAD_NMUX".format(prim), ["1", "LOAD_N"],
            lambda x: get_substs(mode="IREG_OREG", kv=("LOAD_NMUX", x), glb=True), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "{}.INREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="INREG"), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.OUTREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="OUTREG"), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.TSREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="TSREG"), False)
        if not s:
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.MIDDRXN.DDRMODE".format(prim), ["NONE", "MIDDRX2", "MIDDRX4"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x), scope="MIDDRXN"), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODDRXN.DDRMODE".format(prim), ["NONE", "MOSHX2", "MOSHX4", "MODDRX2_DQSW", "MODDRX4_DQSW", "MODDRX2_DQSW270", "MODDRX4_DQSW270"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x), scope="MODDRXN", dqs=True), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.MTDDRXN.DDRMODE".format(prim), ["NONE", "MTSHX2", "MTSHX4"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x + " TOUTMUX:MTDDR"), scope="MTDDRXN"), False)
    fuzzloops.parallel_foreach(configs, per_config)

if __name__ == "__main__":
    main()
