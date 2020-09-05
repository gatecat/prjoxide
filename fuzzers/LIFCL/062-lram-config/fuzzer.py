from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ("LRAM_CORE_R18C86", "LRAM0", FuzzConfig(job="LRAM0", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R23C87:LRAM_0" ])),
    ("LRAM_CORE_R40C86", "LRAM1", FuzzConfig(job="LRAM1", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R41C87:LRAM_1", ])),
]

def main():
    def per_config(x):
        site, lram, cfg = x
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "lram.v"

        def get_substs(mode="NONE", kv=None, mux=False):
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
            return dict(cmt="//" if mode == "NONE" else "", config=config, site=site)
        modes = ["NONE", "LRAM_CORE"]
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(lram), modes,
            lambda x: get_substs(mode=x), False,
            desc="{} primitive mode".format(lram))
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.ASYNC_RST_RELEASE".format(lram), ["SYNC", "ASYNC"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("ASYNC_RST_RELEASE", x)), False,
            desc="LRAM reset release configuration")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.DATA_PRESERVE".format(lram), ["DISABLE", "ENABLE"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("DATA_PRESERVE", x)), False,
            desc="LRAM data preservation across resets")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.EBR_SP_EN".format(lram), ["DISABLE", "ENABLE"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("EBR_SP_EN", x)), False,
            desc="EBR single port mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.ECC_BYTE_SEL".format(lram), ["ECC_EN", "BYTE_EN"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("ECC_BYTE_SEL", x)), False,
            desc="")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.GSR".format(lram), ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("GSR", x)), False,
            desc="LRAM global set/reset mask")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.OUT_REGMODE_A".format(lram), ["NO_REG", "OUT_REG"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("OUT_REGMODE_A", x)), False,
            desc="LRAM output pipeline register A enable")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.OUT_REGMODE_B".format(lram), ["NO_REG", "OUT_REG"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("OUT_REGMODE_B", x)), False,
            desc="LRAM output pipeline register B enable")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.RESETMODE".format(lram), ["SYNC", "ASYNC"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("RESETMODE", x)), False,
            desc="LRAM sync/async reset select")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.RST_AB_EN".format(lram), ["RESET_AB_DISABLE", "RESET_AB_ENABLE"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("RST_AB_EN", x)), False,
            desc="LRAM reset A/B enable")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.SP_EN".format(lram), ["DISABLE", "ENABLE"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("SP_EN", x)), False,
            desc="LRAM single port mode")
        nonrouting.fuzz_enum_setting(cfg, empty, "{}.UNALIGNED_READ".format(lram), ["DISABLE", "ENABLE"],
            lambda x: get_substs(mode="LRAM_CORE", kv=("UNALIGNED_READ", x)), False,
            desc="LRAM unaligned read support")
        for port in ("CLK", "CSA", "CSB", "CEA", "CEB", "RSTA", "RSTB", "OCEA", "OCEB", "WEA", "WEB"):
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}MUX".format(lram, port), [port, "INV"],
                lambda x: get_substs(mode="LRAM_CORE", kv=(port, x), mux=True), False,
                desc="LRAM {} inversion control".format(port))
    fuzzloops.parallel_foreach(configs, per_config)
if __name__ == "__main__":
    main()
