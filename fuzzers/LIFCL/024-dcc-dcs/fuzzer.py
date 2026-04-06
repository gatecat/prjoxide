from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import lapie
import database


def per_site(dev, site, dcc_tiles, dcs_tiles):
    if site.startswith("DCC"):
        cfg = FuzzConfig(job=site, device=dev, tiles=dcc_tiles)
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "dcc.v"

        def get_substs(dccen):
            return dict(dev=dev, site=site, dccen=dccen)

        nonrouting.fuzz_enum_setting(cfg, empty, "{}.DCCEN".format(site), ["0", "1"],
                                     lambda x: get_substs(x), False,
                                     desc="DCC bypassed (0) or used as gate (1)")
    else:
        assert site.startswith("DCS")
        cfg = FuzzConfig(job=site, device=dev, tiles=dcs_tiles)
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "dcs.v"

        def get_substs(dcsmode):
            return dict(dev=dev, site=site, dcsmode=dcsmode)

        nonrouting.fuzz_enum_setting(cfg, empty, "{}.DCSMODE".format(site),
                                     ["GND", "DCS", "DCS_1", "BUFGCECLK0", "BUFGCECLK0_1", "BUFGCECLK1", "BUFGCECLK1_1",
                                      "BUF0", "BUF1", "VCC"],
                                     lambda x: get_substs(x), False,
                                     desc="clock selector mode")
def main():
    # 40k
    dev = "LIFCL-40"
    sv = "../shared/empty_40.v"
    dcc_tiles = ["CIB_R28C0:LMID", "CIB_R28C87:RMID_DLY20", "CIB_R56C49:BMID_0_ECLK_1", "CIB_R56C50:BMID_1_ECLK_2",
        "CIB_R0C49:TMID_0", "CIB_R0C50:TMID_1", "CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1", "CIB_R38C49:CMUX_2", "CIB_R38C50:CMUX_3"]
    dcs_tiles = ["CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1", "CIB_R38C49:CMUX_2", "CIB_R38C50:CMUX_3"]
    dcc_prims = ["DCC_L{}".format(i) for i in range(12)] + \
                ["DCC_R{}".format(i) for i in range(12)] + \
                ["DCC_T{}".format(i) for i in range(16)] + \
                ["DCC_B{}".format(i) for i in range(18)] + \
                ["DCC_C{}".format(i) for i in range(4)]
    dcs_prims = ["DCS0", ]

    fuzzloops.parallel_foreach(dcc_prims + dcs_prims, lambda site: per_site("LIFCL-40", site, dcc_tiles, dcs_tiles))

    #17k
    dev = "LIFCL-17"
    sv = "../shared/empty_17.v"
    dcc_prims = ["DCC_L{}".format(i) for i in range(12)] + \
                ["DCC_R{}".format(i) for i in range(12)] + \
                ["DCC_T{}".format(i) for i in range(16)]
    dcc_tiles = ["CIB_R10C0:LMID_RBB_5_15K", "CIB_R10C75:RMID_PICB_DLY10", "CIB_R0C37:TMID_0", "CIB_R0C38:TMID_1_15K", "CIB_R0C39:CLKBUF_T_15K"]
    fuzzloops.parallel_foreach(dcc_prims, lambda site: per_site("LIFCL-17", site, dcc_tiles, dcs_tiles))

    for dev in ["LIFCL-33", "LIFCL-33U"]:

        dcc_prims = [s for s in database.get_sites(dev) if "DCC_" in s]

        dcc_tiles = [x for x in database.get_tilegrid(dev)['tiles'] if "MID" in x]
        dcs_tiles = [x for x in database.get_tilegrid(dev)['tiles'] if "CMUX" in x]

        print(dcc_tiles, dcs_tiles)

        fuzzloops.parallel_foreach(dcc_prims + dcs_prims, lambda site: per_site(dev, site, dcc_tiles, dcs_tiles))

if __name__ == '__main__':
    main()
