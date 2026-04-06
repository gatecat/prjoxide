import logging

from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
from interconnect import fuzz_interconnect, fuzz_interconnect_pins
import tiles

cfgs = [
    FuzzConfig(job="OSCMODE17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R0C71:OSC_15K"]),
    FuzzConfig(job="OSCMODE33", device="LIFCL-33", sv="../shared/empty_33.v", tiles=["CIB_R0C29:OSC"]),
    FuzzConfig(job="OSCMODE33U", device="LIFCL-33U", sv="../shared/empty_33.v", tiles=["CIB_R0C29:OSC"]),        
    FuzzConfig(job="OSCMODE40", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C77:EFB_1_OSC"]),
]

def main(executor):
    for cfg in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "osc.v"

        def bin_to_int(x):
            val = 0
            mul = 1
            for bit in x:
                if bit:
                    val |= mul
                mul *= 2
            return val

        sites = tiles.get_sites_from_primitive(cfg.device, "OSC_CORE")
        if len(sites) == 0:
            logging.error(f"No OSC_CORE's defined for {cfg.device}")
            continue

        site = list(sites.keys())[0]
        
        def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False):
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
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.MODE", ["NONE", "OSC_CORE"],
            lambda x: get_substs(mode=x), False,
            desc="OSC_CORE primitive mode")
        nonrouting.fuzz_word_setting(cfg, "OSC_CORE.HF_CLK_DIV", 8,
            lambda x: get_substs(mode="OSC_CORE", kv=("HF_CLK_DIV", str(bin_to_int(x)))),
            desc="high frequency oscillator output divider")
        nonrouting.fuzz_word_setting(cfg, "OSC_CORE.HF_SED_SEC_DIV", 8,
            lambda x: get_substs(mode="OSC_CORE", kv=("HF_SED_SEC_DIV", str(bin_to_int(x)))),
            desc="high frequency oscillator output divider")

        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.DTR_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("DTR_EN", x)), False,
            desc="")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HF_FABRIC_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("HF_FABRIC_EN", x)), False,
            desc="enable HF oscillator trimming from input pins")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HF_OSC_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("HF_OSC_EN", x)), False,
            desc="enable HF oscillator")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.HFDIV_FABRIC_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("HFDIV_FABRIC_EN", x)), False,
            desc="enable HF divider from parameter")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.LF_FABRIC_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("LF_FABRIC_EN", x)), False,
            desc="enable LF oscillator trimming from input pins")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.LF_OUTPUT_EN", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("LF_OUTPUT_EN", x)), False,
            desc="enable LF oscillator output")
        nonrouting.fuzz_enum_setting(cfg, empty, "OSC_CORE.DEBUG_N", ["ENABLED", "DISABLED"],
            lambda x: get_substs(mode="OSC_CORE", kv=("DEBUG_N", x)), False,
            desc="enable debug mode")

        rc = tiles.get_rc_from_name(cfg.device, cfg.tiles[0])
        # Fuzz oscillator routing
        regex = False
        full_mux = False
        if cfg.device == "LIFCL-17":
            cfg.sv = "../shared/route_17.v"
            regex = True
            nodes = [".*_OSC_CORE"]            
        elif cfg.device.startswith("LIFCL-33"):
            #cfg.sv = "osc_pins.v"
            cfg.sv = "../shared/route_33.v"            
            regex = True
            nodes = [".*_OSC_CORE" ]
            full_mux = True
#            DTR_EN:#ON HF_CLK_DIV:::HF_CLK_DIV=+1 HF_SED_SEC_DIV:::HF_SED_SEC_DIV=+1 HF_FABRIC_EN:#ON HF_OSC_EN:#ON HFDIV_FABRIC_EN:#ON LF_FABRIC_EN:#ON LF_OUTPUT_EN:#ON DEBUG_N:#ON
#            OSC_CORE:::LF_FABRIC_EN=ENABLED OSC_CORE:::HF_FABRIC_EN=ENABLED OSC_CORE:::DTR_EN=ENABLED OSC_CORE:::HF_OSC_EN=ENABLED OSC_CORE:::HFDIV_FABRIC_EN=ENABLED
#fuzz_interconnect_pins(cfg, "OSC_CORE_R1C29", {"config": "OSC_CORE:::LF_FABRIC_EN=ENABLED OSC_CORE:::HF_FABRIC_EN=ENABLED OSC_CORE:::DTR_EN=ENABLED OSC_CORE:::HF_OSC_EN=ENABLED OSC_CORE:::HFDIV_FABRIC_EN=ENABLED OSC_CORE:::DEBUG_N=DISABLED OSC_CORE:::HF_CLK_DIV=1 OSC_CORE:::HF_SED_SEC_DIV=1"})
        else:
            cfg.sv = "../shared/route_40.v"
            nodes = ["R1C77_JLFCLKOUT_OSC_CORE", "R1C77_JHFCLKOUT_OSC_CORE",
                "R1C77_JHFSDCOUT_OSC_CORE", "R1C77_JHFCLKCFG_OSC_CORE",
                "R1C77_JHFOUTEN_OSC_CORE", "R1C77_JHFSDSCEN_OSC_CORE"]
            for i in range(9):
                nodes.append("R1C77_JHFTRMFAB{}_OSC_CORE".format(i))
                nodes.append("R1C77_JLFTRMFAB{}_OSC_CORE".format(i))
        fuzz_interconnect(config=cfg, nodenames=nodes, regex=regex, bidir=True, full_mux_style=full_mux)

        
if __name__ == '__main__':
    fuzzloops.FuzzerMain(main)
