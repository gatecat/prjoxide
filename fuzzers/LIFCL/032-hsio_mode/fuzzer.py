from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ("A","V1", # PB6A
        FuzzConfig(job="IO5A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C6:SYSIO_B5_0", "CIB_R56C7:SYSIO_B5_1"])),
    ("B","W1", # PB6B
        FuzzConfig(job="IO5B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C6:SYSIO_B5_0", "CIB_R56C7:SYSIO_B5_1"])),
    ("A","Y7", # PB30A
        FuzzConfig(job="IO4A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C30:SYSIO_B4_0", "CIB_R56C31:SYSIO_B4_1"])),
    ("B","Y8", # PB30B
        FuzzConfig(job="IO4B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C30:SYSIO_B4_0", "CIB_R56C31:SYSIO_B4_1"])),
    ("A","R12", # PB64A
        FuzzConfig(job="IO3A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C64:SYSIO_B3_0", "CIB_R56C65:SYSIO_B3_1"])),
    ("B","P12", # PB64A
        FuzzConfig(job="IO3B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C64:SYSIO_B3_0", "CIB_R56C65:SYSIO_B3_1"])),


]

seio_types = [
    ("LVCMOS18H", 1.8, None),
    ("LVCMOS15H", 1.5, None),
    ("LVCMOS12H", 1.2, None),
    ("LVCMOS10H", 1.0, None),
    ("LVCMOS10R", 1.8, ["INPUT"]),
    ("SSTL135_I", 1.35, None),
    ("SSTL135_II", 1.35, None),
    ("SSTL15_I", 1.5, None),
    ("SSTL15_II", 1.5, None),
    ("HSTL15_I", 1.5, None),
    ("HSUL12", 1.2, None),
#    ("MIPI_DPHY", 1.2, None),
#    ("VREF1_DRIVER", 1.5, ["OUTPUT"]),
#    ("VREF2_DRIVER", 1.5, ["OUTPUT"]),
]

diffio_types = [
    ("LVDS", 1.8, None),
    ("SUBLVDS", 1.8, ["INPUT"]),
    ("SUBLVDSEH", 1.8, ["OUTPUT"]),
    ("SLVS", 1.2, None),
    ("MIPI_DPHY", 1.2, None),
    ("SSTL135D_I", 1.35, None),
    ("SSTL135D_II", 1.35, None),
    ("SSTL15D_I", 1.5, None),
    ("SSTL15D_II", 1.5, None),
    ("HSTL15D_I", 1.5, None),
    ("HSUL12D", 1.2, None),
]
def main():
    def per_config(config):
        pio, site, cfg = config
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "iob_40.v"
        def get_bank_vccio(iotype):
            if iotype == "NONE":
                return "1.8"
            else:
                for t, v, d in (seio_types + diffio_types):
                    if t == iotype:
                        return str(v)
        def is_diff(iotype):
            for t, v, d in diffio_types:
                if t == iotype:
                    return True
            return False
        def get_substs(iotype="BIDIR_LVCMOS18H", kv=None, vcc=None, tmux="T"):
            iodir, iostd = iotype.split("_", 1) if iotype != "NONE" else ("","")
            if iodir == "INPUT":
                pintype = "input"
                t = "1"
            elif iodir == "OUTPUT":
                pintype = "output"
                t = "0"
            else:
                pintype = "inout"
                if tmux == "INV":
                    t = "#INV"
                else:
                    t = "#SIG"
            if kv is not None:
                extra_config = ",{}={}".format(kv[0], kv[1])
            else:
                extra_config = ""
            if vcc is None:
                vcc = get_bank_vccio(iostd)
            if is_diff(iostd):
                primtype = "DIFFIO18_CORE"
            else:
                primtype = "SEIO18_CORE"
            return dict(cmt="//" if iotype == "NONE" else "",
                pintype=pintype, primtype=primtype, site=site, iotype=iostd, t=t, extra_config=extra_config, vcc=vcc)
        all_se_types = ["NONE"]
        all_di_types = ["NONE"]
        for t, v, d in seio_types:
            if d is None:
                all_se_types += ["INPUT_{}".format(t), "BIDIR_{}".format(t), "OUTPUT_{}".format(t)]
            else:
                all_se_types += ["{}_{}".format(di, t) for di in d]
        for t, v, d in diffio_types:
            if d is None:
                all_di_types += ["INPUT_{}".format(t), "BIDIR_{}".format(t), "OUTPUT_{}".format(t)]
            else:
                all_di_types += ["{}_{}".format(di, t) for di in d]

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.BASE_TYPE".format(pio), all_se_types,
                lambda x: get_substs(iotype=x), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DRIVE_1V8".format(pio), ["2", "4", "8", "12", "50RS"],
                lambda x: get_substs(iotype="OUTPUT_LVCMOS18H", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DRIVE_1V5".format(pio), ["2", "4", "8"],
                lambda x: get_substs(iotype="OUTPUT_LVCMOS15H", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DRIVE_1V2".format(pio), ["2", "4", "8"],
                lambda x: get_substs(iotype="OUTPUT_LVCMOS12H", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DRIVE_1V0".format(pio), ["2", "4"],
                lambda x: get_substs(iotype="OUTPUT_LVCMOS10H", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DRIVE_HSUL12".format(pio), ["4", "6", "8"],
                lambda x: get_substs(iotype="OUTPUT_HSUL12", kv=("DRIVE", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.PULLMODE".format(pio), ["NONE", "UP", "DOWN", "KEEPER"],
                lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("PULLMODE", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.UNDERDRIVE_1V8".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H" if x=="OFF" else "INPUT_LVCMOS15H", vcc="1.8"), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.SLEWRATE".format(pio), ["SLOW", "MED", "FAST"],
                lambda x: get_substs(iotype="OUTPUT_LVCMOS18H", kv=("SLEWRATE", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.TERMINATION_1V8".format(pio), ["OFF", "40", "50", "60", "75", "150"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("TERMINATION", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.TERMINATION_1V5".format(pio), ["OFF", "40", "50", "60", "75"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS15H", kv=("TERMINATION", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.TERMINATION_1V35".format(pio), ["OFF", "40", "50", "60", "75"],
                        lambda x: get_substs(iotype="INPUT_SSTL135_I", kv=("TERMINATION", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.TERMINATION_1V2".format(pio), ["OFF", "40", "50", "60", "75"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS12H", kv=("TERMINATION", x)), False)


        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.DFTDO2DI".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("DFTDO2DI", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.LOOPBKCD2AB".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("LOOPBKCD2AB", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.OPENDRAIN".format(pio), ["OFF", "ON"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS18H", kv=("OPENDRAIN", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.SLEEPHIGHLEAKAGE".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("SLEEPHIGHLEAKAGE", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.ENADC_IN".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("ENADC_IN", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.INT_LPBK".format(pio), ["DISABLED", "ENABLED"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS18H", kv=("INT_LPBK", x)), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.VREF".format(pio), ["OFF", "VREF1_LOAD", "VREF2_LOAD"],
            lambda x: get_substs(iotype="INPUT_SSTL135_I", kv=("VREF", x)), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.TMUX".format(pio), ["T", "INV"],
                    lambda x: get_substs(iotype="BIDIR_LVCMOS18H", tmux=x), False)

        if pio == "A":
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.BASE_TYPE".format(pio), all_di_types,
                            lambda x: get_substs(iotype=x), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.PULLMODE".format(pio), ["NONE", "FAILSAFE"],
                            lambda x: get_substs(iotype="INPUT_LVDS", kv=("PULLMODE", x)), True)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFRESISTOR".format(pio), ["OFF", "100"],
                            lambda x: get_substs(iotype="INPUT_LVDS", kv=("DIFFRESISTOR", x)), True)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFDRIVE_MIPI_DPHY".format(pio), ["NA", "2P0"],
                            lambda x: get_substs(iotype="OUTPUT_MIPI_DPHY", kv=("DIFFDRIVE", x.replace("P", "."))), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFDRIVE_SLVS".format(pio), ["NA", "2P0"],
                            lambda x: get_substs(iotype="OUTPUT_SLVS", kv=("DIFFDRIVE", x.replace("P", "."))), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFDRIVE_LVDS".format(pio), ["NA", "3P5"],
                            lambda x: get_substs(iotype="OUTPUT_LVDS", kv=("DIFFDRIVE", x.replace("P", "."))), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFRX_INV".format(pio), ["NORMAL", "INVERT"],
                            lambda x: get_substs(iotype="INPUT_LVDS", kv=("DIFFRX_INV", x)), False)
            nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DIFFIO18.DIFFTX_INV".format(pio), ["NORMAL", "INVERT"],
                            lambda x: get_substs(iotype="OUTPUT_LVDS", kv=("DIFFTX_INV", x)), False)
    fuzzloops.parallel_foreach(configs, per_config)
if __name__ == "__main__":
    main()
