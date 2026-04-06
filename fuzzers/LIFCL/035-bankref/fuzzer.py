from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    (1, "F16",
        FuzzConfig(job="IO1A_17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R2C75:BK1_15K"])),
    (0, "E15",
        FuzzConfig(job="IO0A_17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R0C56:BK0_15K"])),
    (5, "M3",
        FuzzConfig(job="IO5A_17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R29C13:V51_15K", "CIB_R29C31:SYSIO_B5_1_15K_ECLK_L_V52", "CIB_R29C32:IO_B4_0_15K_DLY52_BK5"])),
    (4, "T3",
        FuzzConfig(job="IO4A_17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R29C52:SYSIO_B4_0_15K_BK4_V42", "CIB_R29C35:IO_B4_1_15K_V41"])),
    (3, "T12",
        FuzzConfig(job="IO3A_17", device="LIFCL-17", sv="../shared/empty_17.v", tiles=["CIB_R29C72:BK3_15K", "CIB_R29C54:SYSIO_B4_0_15K_V31", "CIB_R29C73:DDR_OSC_R_15K_V32"])),

    (1, "F16",
        FuzzConfig(job="IO1A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R9C87:BANKREF1"])),
    (2, "N14",
        FuzzConfig(job="IO2A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R39C87:BANKREF2"])),
    (6, "R3",
        FuzzConfig(job="IO6A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R35C0:BANKREF6"])),
    (7, "E2",
        FuzzConfig(job="IO7A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R9C0:BANKREF7_RBB_2"])),
    (0, "E18",
        FuzzConfig(job="IO0A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C72:BANKREF0"])),
    (5, "V1",
        FuzzConfig(job="IO5A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C14:BANKREF5_V18_ECLK_L", "CIB_R56C13:SYSIO_B5_1_V18", "CIB_R56C2:DOSCL_P18_V18"])),
    (4, "R7",
        FuzzConfig(job="IO4A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C52:BANKREF4_V18", "CIB_R56C14:BANKREF5_V18_ECLK_L", "CIB_R56C2:DOSCL_P18_V18"])),
    (3, "U12",
        FuzzConfig(job="IO3A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R55C87:BANKREF3", "CIB_R56C85:SYSIO_B3_1_V18", "CIB_R56C54:SYSIO_B3_0_DLY30_V18", "CIB_R56C52:BANKREF4_V18", "CIB_R56C2:DOSCL_P18_V18"])),

]

vcc_to_io_33 = {
    "NONE": "NONE",
    "1V2": "LVCMOS12",
    "1V5": "LVCMOS15",
    "1V8": "LVCMOS18",
    "2V5": "LVCMOS25",
    "3V3": "LVCMOS33"
}

vcc_to_io_18 = {
    "NONE": "NONE",
    "1V0": "LVCMOS10H",
    "1V2": "LVCMOS12H",
    "1V5": "LVCMOS15H",
    "1V8": "LVCMOS18H",
}


def main():
    def per_config(config):
        bank, site, cfg = config
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        if cfg.device == "LIFCL-17":
            cfg.sv = "../031-io_mode/iob_17.v"
        else:
            cfg.sv = "../031-io_mode/iob_40.v"
        def get_substs(iotype="LVCMOS18H", kv=None, vcc=None, diff=False, tmux="#SIG"):
            if kv is not None:
                extra_config = ",{}={}".format(kv[0], kv[1])
            else:
                extra_config = ""
            if diff:
                primtype = "DIFFIO18_CORE"
            elif bank in (3, 4, 5):
                primtype = "SEIO18_CORE"
            else:
                primtype = "SEIO33_CORE"
            return dict(cmt="//" if iotype == "NONE" else "",
                pintype="inout", primtype=primtype, site=site, iotype=iotype, t=tmux, extra_config=extra_config, vcc=vcc)
        if bank in (3, 4, 5):
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.VCC".format(bank), ["NONE", "1V0", "1V2", "1V5", "1V8"],
                        lambda x: get_substs(iotype=vcc_to_io_18[x], vcc=x.replace("V", ".")), False,
                        assume_zero_base=True,
                        desc="VccIO of bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.DIFF_IO".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype=("SSTL15D_I" if x == "ON" else "SSTL15_I"), diff=(x == "ON"), vcc="1.5"), False,
                        desc="use differential IO in bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.REF_IO".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype=("SSTL15_I" if x == "ON" else "LVCMOS15H"), vcc="1.5"), False,
                        desc="use referenced inputs in bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.LVDS_IO".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype=("LVDS" if x == "ON" else "LVCMOS18H"), diff=True, vcc="1.8"), False,
                        desc="use LVDS IO in bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.SLVS_IO".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype=("SLVS" if x == "ON" else "HSUL12"), diff=(x == "ON"), vcc="1.2"), False,
                        desc="use SLVS IO in bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.MIPI_DPHY_IO".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype=("MIPI_DPHY" if x == "ON" else "HSUL12"), diff=(x == "ON"), vcc="1.2"), False,
                        desc="use DPHY IO in bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.VREF1_USED".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype="SSTL15_I", vcc="1.5", kv=("VREF", "VREF1_LOAD" if x == "ON" else "OFF")), False,
                        desc="use VREF1 input for bank {}".format(bank))
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.VREF2_USED".format(bank), ["OFF", "ON"],
                        lambda x: get_substs(iotype="SSTL15_I", vcc="1.5", kv=("VREF", "VREF2_LOAD" if x == "ON" else "OFF")), False,
                        desc="use VREF2 input for bank {}".format(bank))
        else:  
            nonrouting.fuzz_enum_setting(cfg, empty, "BANK{}.VCC".format(bank), ["NONE", "1V2", "1V5", "1V8", "2V5", "3V3"],
                        lambda x: get_substs(iotype=vcc_to_io_33[x], vcc=x.replace("V", ".")), False,
                        assume_zero_base=True,
                        desc="VccIO of bank {}".format(bank))
    fuzzloops.parallel_foreach(configs, per_config)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
