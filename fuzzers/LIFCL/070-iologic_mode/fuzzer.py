import asyncio

from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [

    # LIFCL-40 tiles
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

    ("IOL_R3B", "SIOLOGICB", FuzzConfig(job="IOL3DEMODE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R3C87:SYSIO_B1_DED"])),

    # LIFCL-17 tiles
    ("IOL_T57A", "SIOLOGICA", FuzzConfig(job="IOLT57AMODE", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R0C57:SYSIO_B0_0_15K"])),
    ("IOL_T57B", "SIOLOGICB", FuzzConfig(job="IOLT57BMODE", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R0C57:SYSIO_B0_0_15K"])),

    ("IOL_R3B", "SIOLOGICB", FuzzConfig(job="IOLR3BMODE", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R3C75:SYSIO_B1_DED_15K", "CIB_R4C75:PIC_B1_DED_15K"])),

    ("IOL_R5A", "SIOLOGICA", FuzzConfig(job="IOLR5AMODE", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R5C75:SYSIO_B1_0_15K"])),
    ("IOL_R5B", "SIOLOGICB", FuzzConfig(job="IOLR5BMODE", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R5C75:SYSIO_B1_0_15K"])),

    # It appears that LIFCL-17 does not expose any pins from
    # - SYSIO_B1_1_15K
]

async def main(executor):
    async def per_config(x):
        site, prim, cfg = x
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})

        if cfg.device == "LIFCL-40":
            cfg.sv = "iologic_40.v"
        elif cfg.device == "LIFCL-17":
            cfg.sv = "iologic_17.v"
        else:
            assert False, cfg.device

        s = (prim[0] == "S")

        side = site[4]
        pos = int(site[5:-1])
        ab = site[-1]

        if cfg.device == "LIFCL-40":
            if side == "L":
                rc = "R{}C{}".format(pos, 0)
            elif side == "R":
                rc = "R{}C{}".format(pos, 87)
            elif side == "B":
                rc = "R{}C{}".format(56, pos)
            elif side == "T":
                rc = "R{}C{}".format(0, pos)
        elif cfg.device == "LIFCL-17":
            if side == "L":
                rc = "R{}C{}".format(pos, 0)
            elif side == "R":
                rc = "R{}C{}".format(pos, 75)
            elif side == "B":
                rc = "R{}C{}".format(29, pos)
            elif side == "T":
                rc = "R{}C{}".format(0, pos)
        else:
            assert False, cfg.device

        futures = []
        def fuzz_enum_setting(*args, **kwargs):
            futures.append(fuzzloops.wrap_future(nonrouting.fuzz_enum_setting(cfg, empty, *args, **kwargs,executor=executor)))

        def get_substs(mode="NONE", default_cfg=False, scope=None, kv=None, mux=False, glb=False, dqs=False, pinconn=""):
            if default_cfg:
                config = "SCLKINMUX:#OFF GSR:ENABLED INMUX:#OFF OUTMUX:#OFF DELAYMUX:#OFF CEOUTMUX:#OFF CEINMUX:#OFF LSRINMUX:#OFF LSROUTMUX:#OFF STOP_EN:DISABLED"
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
            if pinconn != "":
                # Add routing so that pin is 'used'
                if "TOUT" in pinconn:
                    if side in ("L", "R", "T"):
                        first_wire = "{}_JTOUT_SIOLOGIC_CORE_IBASE_PIC_{}".format(rc, ab)
                        second_wire = "{}_JPADDT_SEIO33_CORE_IO{}".format(rc, ab)
                    else:
                        first_wire = "{}_JTOUT_IOLOGIC_CORE_I_GEARING_PIC_TOP_{}".format(rc, ab)
                        if ab == "A":
                            second_wire = "{}_JPADDT_DIFFIO18_CORE_IO{}".format(rc, ab)
                        else:
                            second_wire = "{}_JPADDT_SEIO18_CORE_IO{}".format(rc, ab)
                else:
                    if side in ("L", "R", "T"):
                        first_wire = "{}_JDOUT_SIOLOGIC_CORE_IBASE_PIC_{}".format(rc, ab)
                        second_wire = "{}_JPADDO_SEIO33_CORE_IO{}".format(rc, ab)
                    else:
                        first_wire = "{}_JDOUT_IOLOGIC_CORE_I_GEARING_PIC_TOP_{}".format(rc, ab)
                        if ab == "A":
                            second_wire = "{}_JPADDO_DIFFIO18_CORE_IO{}".format(rc, ab)
                        else:
                            second_wire = "{}_JPADDO_SEIO18_CORE_IO{}".format(rc, ab)
                route = '(* \\xref:LOG ="q_c@0@9", \\dm:arcs ="{}.{}" *) '.format(second_wire, first_wire)
                sig = route + "wire sig;"
            else:
                sig = ""
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site, s="S" if s else "", pinconn=pinconn, sig=sig)
        modes = ["NONE", "IREG_OREG", "IDDRX1_ODDRX1"]
        if not s:
            modes += ["IDDRXN", "ODDRXN", "MIDDRXN_MODDRXN"]
        fuzz_enum_setting("{}.MODE".format(prim), modes,
            lambda x: get_substs(x, default_cfg=True), False)
        fuzz_enum_setting("{}.GSR".format(prim), ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="IREG_OREG", kv=("GSR", x), glb=True), False)
        fuzz_enum_setting("{}.SRMODE".format(prim), ["ASYNC", "LSR_OVER_CE"],
            lambda x: get_substs(mode="IREG_OREG", kv=("SRMODE", x), glb=True), False)
        if not s:
            fuzz_enum_setting("{}.IDDRXN.DDRMODE".format(prim), ["NONE", "IDDRX2", "IDDR71", "IDDRX4", "IDDRX5"],
                lambda x: get_substs(mode="IDDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x)), False)
            fuzz_enum_setting("{}.ODDRXN.DDRMODE".format(prim), ["ODDRX2", "ODDR71", "ODDRX4", "ODDRX5"],
                lambda x: get_substs(mode="ODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x)), False)

        for sig in ("SCLKIN", "SCLKOUT", "CEIN", "CEOUT", "LSRIN", "LSROUT"):
            fuzz_enum_setting("{}.{}MUX".format(prim, sig), ["1" if sig[0:2] == "CE" else "0", sig, "INV"],
                lambda x: get_substs(mode="IREG_OREG", kv=("{}MUX".format(sig), x), mux=True), False)

        fuzz_enum_setting("{}.IDDRX1_ODDRX1.OUTPUT".format(prim), ["DISABLED", "ENABLED"],
            lambda x: get_substs(mode="IDDRX1_ODDRX1", default_cfg=True, pinconn=(".DOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)
        fuzz_enum_setting("{}.IREG_OREG.OUTPUT".format(prim), ["DISABLED", "ENABLED"],
            lambda x: get_substs(mode="IREG_OREG", default_cfg=True, pinconn=(".DOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)

        if not s:
            fuzz_enum_setting("{}.IDDRX1_ODDRX1.TRISTATE".format(prim), ["DISABLED", "ENABLED"],
                lambda x: get_substs(mode="IDDRX1_ODDRX1", kv=("TOUTMUX", "TSREG"), glb=True, pinconn=(".TOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)
            fuzz_enum_setting("{}.IREG_OREG.TRISTATE".format(prim), ["DISABLED", "ENABLED"],
                lambda x: get_substs(mode="IREG_OREG", kv=("TOUTMUX", "TSREG"), glb=True, pinconn=(".TOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)
        else:
            fuzz_enum_setting("{}.IDDRX1_ODDRX1.TRISTATE".format(prim), ["DISABLED", "ENABLED"],
                lambda x: get_substs(mode="IDDRX1_ODDRX1", default_cfg=True, pinconn=(".TOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)
            fuzz_enum_setting("{}.IREG_OREG.TRISTATE".format(prim), ["DISABLED", "ENABLED"],
                lambda x: get_substs(mode="IREG_OREG", default_cfg=True, pinconn=(".TOUT(sig), .LSRIN(sig)" if x == "ENABLED" else "")), False)

        fuzz_enum_setting("{}.INMUX".format(prim), ["BYPASS", "DELAY"],
            lambda x: get_substs(mode="IREG_OREG", kv=("INMUX", x), glb=True), False)
        fuzz_enum_setting("{}.OUTMUX".format(prim), ["BYPASS", "DELAY"],
            lambda x: get_substs(mode="IREG_OREG", kv=("OUTMUX", x), glb=True), False)
        fuzz_enum_setting("{}.DELAYMUX".format(prim), ["OUT_REG", "IN"],
            lambda x: get_substs(mode="IREG_OREG", kv=("DELAYMUX", x), glb=True), False)

        if not s:
            fuzz_enum_setting("{}.MOVEMUX".format(prim), ["0", "MOVE"],
                lambda x: get_substs(mode="IREG_OREG", kv=("MOVEMUX", x), glb=True), False)
            fuzz_enum_setting("{}.DIRMUX".format(prim), ["0", "DIR"],
                lambda x: get_substs(mode="IREG_OREG", kv=("DIRMUX", x), glb=True), False)
            fuzz_enum_setting("{}.LOAD_NMUX".format(prim), ["1", "LOAD_N"],
                lambda x: get_substs(mode="IREG_OREG", kv=("LOAD_NMUX", x), glb=True), False)

        fuzz_enum_setting("{}.INREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="INREG"), False)
        fuzz_enum_setting("{}.OUTREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="OUTREG"), False)
        fuzz_enum_setting("{}.TSREG.REGSET".format(prim), ["SET", "RESET"],
            lambda x: get_substs(mode="IREG_OREG", kv=("REGSET", x), scope="TSREG"), False)
        if not s:
            fuzz_enum_setting("{}.MIDDRXN.DDRMODE".format(prim), ["MIDDRX2", "MIDDRX4"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x), scope="MIDDRXN"), False)
            fuzz_enum_setting("{}.MODDRXN.DDRMODE".format(prim), ["MOSHX2", "MOSHX4", "MODDRX2_DQSW", "MODDRX4_DQSW", "MODDRX2_DQSW270", "MODDRX4_DQSW270"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x), scope="MODDRXN", dqs=True), False)
            fuzz_enum_setting("{}.MTDDRXN.DDRMODE".format(prim), ["MTSHX2", "MTSHX4"],
                lambda x: get_substs(mode="MIDDRXN_MODDRXN", kv=("DDRMODE", "#OFF" if x == "NONE" else x + " TOUTMUX:MTDDR"), scope="MTDDRXN"), False)

        await asyncio.gather(*futures)

    await asyncio.gather(*[per_config(c) for c in configs])

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(main)
