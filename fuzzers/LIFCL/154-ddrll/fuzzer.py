from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import nonrouting
import re
import fuzzloops

configs = [
    {
        "cfg": FuzzConfig(job="DDRDLLL", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C2:DOSCL_P18_V18"]),
        "rc": (55, 2),
    },
    {
        "cfg": FuzzConfig(job="DDRDLLR", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R54C87:DDR_OSC_R"]),
        "rc": (54, 86),
    },
]

ignore_tiles = set([
    "CIB_R55C{}:CIB".format(i) for i in range(1, 87)
] + [
    "CIB_R54C86:CIB_LR",
    "CIB_R53C86:CIB_LR",
    "CIB_R52C86:CIB_LR",
    "CIB_R54C1:CIB_LR",
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("ECLKDDR" in x or "DDRDLL_CORE" in x or "JCLKOUT_I" in x or "JPCLK_I" in x or "JECLK" in x)
        def pip_filter(x, nodes):
            src, snk = x
            return True
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

        cfg.sv = "../shared/empty_40.v"
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "ddrdll.v"

        site = "DDRDLL_CORE_R{}C{}".format(r, c)

        def get_substs(mode="DDRDLL_CORE", kv=None, mux=False):
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
        nonrouting.fuzz_enum_setting(cfg, empty, "DDRDLL.MODE", ["NONE", "DDRDLL_CORE"],
            lambda x: get_substs(mode=x), False,
            desc="DDRDLL primitive mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "DDRDLL.GSR", ["ENABLED", "DISABLED"],
            lambda x: get_substs(kv=("GSR", x)), False,
            desc="DDRDLL GSR mask")
        nonrouting.fuzz_enum_setting(cfg, empty, "DDRDLL.ENA_ROUNDOFF", ["ENABLED", "DISABLED"],
            lambda x: get_substs(kv=("ENA_ROUNDOFF", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "DDRDLL.FORCE_MAX_DELAY", ["CODE_OR_LOCK_FROM_DLL_LOOP", "FORCE_LOCK_AND_CODE"],
            lambda x: get_substs(kv=("FORCE_MAX_DELAY", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "DDRDLL.RSTMUX", ["RST", "INV"],
            lambda x: get_substs(kv=("RST", x), mux=True), False)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

