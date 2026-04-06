import asyncio

from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

import tiles


def create_cfgs(device):
    cfgs = []
    for primitive in ["IOLOGIC_CORE", "SIOLOGIC_CORE"]:
        for (tiletype, infos) in tiles.get_tiletypes_by_primitive(device, "IOLOGIC_CORE").items():
            if tiletype.startswith("SYSIO"):
                print(f"Adding {device} {infos[0]}")
                cfgs.append(
                    (infos[0][0], primitive, FuzzConfig(job=f"{device}_{infos[0][0]}_{infos[0][1]}", device=device, tiles=infos[0][1]))
                )
    return cfgs



configs = create_cfgs("LIFCL-33") + [
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

]

async def main(executor):
    async def per_config(x):
        site, prim, cfg = x
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "iodelay.v"
        s = (prim[0] == "S")


        side = site[4]
        pos = int(site[5:-1])
        ab = site[-1]

        def get_substs(mode="IREG_OREG", deltype="DELAYA", kv=None, mux=False):
            if s and deltype == "DELAYA":
                deltype = "DELAYB"
            if kv is not None:
                if mux:
                    if kv[1] == "OFF":
                        config = "{0}MUX:#OFF".format(kv[0])
                    elif kv[1] == "0":
                        config = "{0}MUX:CONST:::CONST=0".format(kv[0])
                    else:
                        config = "{0}MUX:{0}:::{0}=#SIG".format(kv[0])
                else:
                    config = "{}:::{}={}".format(deltype, kv[0], kv[1])
            else:
                config = ""                
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site, s="S" if s else "", pinconn="", sig="")

        def intval(vec):
            x = 0
            for i, b in enumerate(vec):
                if b:
                    x |= (1 << i)
            return x

        futures = []
        def fuzz_enum_setting(*args, **kwargs):
            futures.append(fuzzloops.wrap_future(nonrouting.fuzz_enum_setting(cfg, empty, *args, **kwargs,executor=executor)))

        def fuzz_word_setting(*args, **kwargs):
            futures.append(fuzzloops.wrap_future(nonrouting.fuzz_word_setting(cfg, *args, **kwargs,executor=executor)))

        fuzz_word_setting("{}.DELAY.DEL_VALUE".format(prim), 7,
                lambda x : get_substs(kv=("DEL_VALUE", str(intval(x)))),
                desc="initial fine delay value")

        fuzz_enum_setting("{}.DELAY.COARSE_DELAY".format(prim), ["0NS", "0P8NS", "1P6NS"],
            lambda x: get_substs(kv=("COARSE_DELAY", x)), False)
        if not s:
            fuzz_enum_setting("{}.DELAY.COARSE_DELAY_MODE".format(prim), ["DYNAMIC", "STATIC"],
                lambda x: get_substs(kv=("COARSE_DELAY_MODE", x)), False)
            fuzz_enum_setting("{}.DELAY.EDGE_MONITOR".format(prim), ["ENABLED", "DISABLED"],
                lambda x: get_substs(kv=("EDGE_MONITOR", x)), False)
            fuzz_enum_setting("{}.DELAY.WAIT_FOR_EDGE".format(prim), ["ENABLED", "DISABLED"],
                lambda x: get_substs(kv=("WAIT_FOR_EDGE", x)), False)

            for pin in ["CIBCRS0", "CIBCRS1", "RANKSELECT", "RANKENABLE", "RANK0UPDATE", "RANK1UPDATE"]:
                fuzz_enum_setting("{}.{}MUX".format(prim, pin), ["OFF", pin],
                    lambda x, pin=pin: get_substs(kv=(pin, x), mux=True), False)

        await asyncio.gather(*futures)

    await asyncio.gather(*[per_config(c) for c in configs])

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(main)
