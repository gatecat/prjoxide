from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import nonrouting
import fuzzloops

import re

configs = [
    {
        "cfg": FuzzConfig(job="DLL70", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R21C0:PCLK_DLY_70_RBB_6"]),
        "rc": (21, 1),
    },
    {
        "cfg": FuzzConfig(job="DLL10", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R21C87:PCLK_DLY_10"]),
        "rc": (21, 86),
    },
    {
        "cfg": FuzzConfig(job="DLL20", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R28C87:RMID_DLY20", "CIB_R29C87:PCLK_DLY_20"]),
        "rc": (28, 86),
    },
    {
        "cfg": FuzzConfig(job="DLL60", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R31C0:PCLK_DLY_60_RBB_8"]),
        "rc": (31, 1),
    },
    {
        "cfg": FuzzConfig(job="DLL50", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C44:SYSIO_B4_0_DLY50", "CIB_R56C45:SYSIO_B4_1_DLY52"]),
        "rc": (55, 44),
    },
    {
        "cfg": FuzzConfig(job="DLL52", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C45:SYSIO_B4_1_DLY52", "CIB_R56C44:SYSIO_B4_0_DLY50"]),
        "rc": (55, 45),
    },
    {
        "cfg": FuzzConfig(job="DLL42", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C46:SYSIO_B4_0_DLY42"]),
        "rc": (55, 46),
    },
    {
        "cfg": FuzzConfig(job="DLL40", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C53:DLY40"]),
        "rc": (55, 53),
    },
    {
        "cfg": FuzzConfig(job="DLL30", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C54:SYSIO_B3_0_DLY30_V18"]),
        "rc": (55, 54),
    },
    {
        "cfg": FuzzConfig(job="DLL32", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C55:SYSIO_B3_1_DLY32"]),
        "rc": (55, 55),
    },
]

ignore_tiles = set([
    "CIB_R55C{}:CIB".format(i) for i in range(1, 87)
] + [
    "CIB_R20C1:CIB_LR",
    "CIB_R20C1:CIB_LR_B",
    "CIB_R21C1:CIB_LR",
    "CIB_R22C1:CIB_LR",
    "CIB_R20C86:CIB_LR",
    "CIB_R21C86:CIB_LR",
    "CIB_R22C86:CIB_LR",
    "CIB_R19C86:CIB_LR_A",
    "CIB_R27C86:CIB_LR",
    "CIB_R28C86:CIB_LR_A",
    "CIB_R29C86:CIB_LR",
    "CIB_R30C86:CIB_LR",
    "CIB_R31C86:CIB_LR"
    "CIB_R29C1:CIB_LR",
    "CIB_R30C1:CIB_LR",
    "CIB_R31C1:CIB_LR",
    "CIB_R32C1:CIB_LR",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("DLLDEL_CORE" in x or "JZ_I4" in x)
        def pip_filter(x, nodes):
            src, snk = x
            return True
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)
    def per_cfg(x):
        cfg = x["cfg"]
        cfg.setup()
        r, c = x["rc"]
        cfg.sv = "../shared/empty_40.v"
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "dlldel.v"

        site = "DLLDEL_CORE_R{}C{}".format(r, c)
        dd = cfg.job[3:]

        def get_substs(mode="DLLDEL_CORE", kv=None, mux=False):
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
            return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site)
        nonrouting.fuzz_enum_setting(cfg, empty, "DLLDEL{}.MODE".format(dd), ["NONE", "DLLDEL_CORE"],
            lambda x: get_substs(mode=x), False,
            desc="DLLDEL primitive mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "DLLDEL{}.ENABLE".format(dd), ["ENABLED", "DISABLED"],
            lambda x: get_substs(kv=("ENABLE", x)), False,
            desc="DLLDEL primitive mode")

        def intval(vec):
            x = 0
            for i, b in enumerate(vec):
                if b:
                    x |= (1 << i)
            return x
        nonrouting.fuzz_enum_setting(cfg, empty, "DLLDEL{}.DEL_ADJUST".format(dd), ["PLUS", "MINUS"],
            lambda x: get_substs(kv=("DEL_ADJUST", x)), False)
        nonrouting.fuzz_word_setting(cfg, "DLLDEL{}.ADJUST".format(dd), 9,
            lambda x: get_substs(kv=("ADJUST", str(intval(x)))))
        nonrouting.fuzz_enum_setting(cfg, empty, "DLLDEL{}.CLKINMUX".format(dd), ["CLKIN", "INV"],
            lambda x: get_substs(kv=("CLKIN", x), mux=True), False)
    fuzzloops.parallel_foreach(configs, per_cfg)
if __name__ == "__main__":
    main()
