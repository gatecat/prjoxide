from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    {
        "cfg": FuzzConfig(job="ECLK0", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C48:ECLK_0", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 48),
        "bank": 5,
    },
    {
        "cfg": FuzzConfig(job="ECLK1", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C48:ECLK_0", "CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 49),
        "bank": 4,
    },
    {
        "cfg": FuzzConfig(job="ECLK2", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C50:BMID_1_ECLK_2", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C48:ECLK_0", "CIB_R56C51:ECLK_3"]),
        "rc": (55, 50),
        "bank": 3,
    },
]

def per_loc(x):
    cfg = x["cfg"]

    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "eclkprim.v"

    r, c = x["rc"]
    bank = x["bank"]
    def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False):
        if kv is None:
            config = ""
        elif mux:
            val = "#SIG"
            if kv[1] in ("0", "1"):
                val = kv[1]
            if kv[1] == "INV":
                val = "#INV"
            config = "{}::::{}={}{}".format(mode, kv[0], val)
        else:
            config = "{}:::{}={}".format(mode, kv[0], kv[1])
        return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, prim=prim, site=site)
    prim = "ECLKSYNC_CORE"
    for z in ['A', 'B', 'C', 'D']:
        site = "ECLKSYNC_CORE_R{}C{}{}".format(r, c, z)
        nonrouting.fuzz_enum_setting(cfg, empty, "ECLKSYNC{}{}.MODE".format(bank, z), ["NONE", "ECLKSYNC"],
            lambda x: get_substs(mode=x), False,
            desc="ECLKSYNC primitive mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "ECLKSYNC{}{}.STOP_EN".format(bank, z), ["DISABLE", "ENABLE"],
            lambda x: get_substs(mode=prim, kv=("STOP_EN", x)), False,
            desc="ECLKSYNC stop control enable")
    prim = "ECLKDIV_CORE"
    for z in ['A', 'B', 'C', 'D']:
        site = "ECLKDIV_CORE_R{}C{}{}".format(r, c, z)
        nonrouting.fuzz_enum_setting(cfg, empty, "ECLKDIV{}{}.GSR".format(bank, z), ["DISABLED", "ENABLED"],
            lambda x: get_substs(mode=prim, kv=("GSR", x)), False,
            desc="ECLKDIV GSR mask")
        nonrouting.fuzz_enum_setting(cfg, empty, "ECLKDIV{}{}.ECLK_DIV".format(bank, z), ["DISABLE", "2", "3P5", "4", "5"],
            lambda x: get_substs(mode=prim, kv=("ECLK_DIV", x)), False,
            desc="ECLKDIV divide value")
def main():
    fuzzloops.parallel_foreach(configs, per_loc)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

