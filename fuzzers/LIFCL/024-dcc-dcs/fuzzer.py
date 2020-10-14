from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

def main():
    dcc_tiles = ["CIB_R28C0:LMID", "CIB_R28C87:RMID_DLY20", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C50:BMID_1_ECLK_2",
        "CIB_R0C49:TMID_0", "CIB_R0C50:TMID_1", "CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1", "CIB_R38C49:CMUX_2", "CIB_R38C50:CMUX_3"]
    dcs_tiles = ["CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1", "CIB_R38C49:CMUX_2", "CIB_R38C50:CMUX_3"]
    dcc_prims = ["DCC_L{}".format(i) for i in range(12)] + \
                ["DCC_R{}".format(i) for i in range(12)] + \
                ["DCC_T{}".format(i) for i in range(16)] + \
                ["DCC_B{}".format(i) for i in range(18)] + \
                ["DCC_C{}".format(i) for i in range(4)]
    dcs_prims = ["DCS0", ]
    def per_site(site):
        if site.startswith("DCC"):
            cfg = FuzzConfig(job=site, device="LIFCL-40", sv="../shared/empty_40.v", tiles=dcc_tiles)
            cfg.setup()
            empty = cfg.build_design(cfg.sv, {})
            cfg.sv = "dcc.v"
            def get_substs(dccen):
                return dict(site=site, dccen=dccen)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.DCCEN".format(site), ["0", "1"],
                lambda x: get_substs(x), False,
                desc="DCC bypassed (0) or used as gate (1)")
        else:
            assert site.startswith("DCS")
            cfg = FuzzConfig(job=site, device="LIFCL-40", sv="../shared/empty_40.v", tiles=dcs_tiles)
            cfg.setup()
            empty = cfg.build_design(cfg.sv, {})
            cfg.sv = "dcs.v"
            def get_substs(dcsmode):
                return dict(site=site, dcsmode=dcsmode)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.DCSMODE".format(site),
                ["GND", "DCS", "DCS_1", "BUFGCECLK0", "BUFGCECLK0_1", "BUFGCECLK1", "BUFGCECLK1_1", "BUF0", "BUF1", "VCC"],
                lambda x: get_substs(x), False,
                desc="clock selector mode")
    fuzzloops.parallel_foreach(dcc_prims + dcs_prims, per_site)
if __name__ == '__main__':
    main()
