from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ("A","F16", # PR8A
        FuzzConfig(job="IO1A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R8C87:SYSIO_B1_0_ODD"])),
    ("B","F17", # PR8B
        FuzzConfig(job="IO1B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R8C87:SYSIO_B1_0_ODD"])),
    ("A","F14", # PR6A
        FuzzConfig(job="IO1A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C87:SYSIO_B1_0_EVEN"])),
    ("B","F15", # PR6B
        FuzzConfig(job="IO1B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C87:SYSIO_B1_0_EVEN"])),
    ("A","F18", # PR10A
        FuzzConfig(job="IC1A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C87:SYSIO_B1_0_C", "CIB_R11C87:SYSIO_B1_0_REM"])),
    ("B","F19", # PR10B
        FuzzConfig(job="IC1B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R10C87:SYSIO_B1_0_C", "CIB_R11C87:SYSIO_B1_0_REM"])),
    ("A","N14", # PR24A
        FuzzConfig(job="IO2A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R24C87:SYSIO_B2_0_EVEN"])),
    ("B","M14", # PR24B
        FuzzConfig(job="IO2B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R24C87:SYSIO_B2_0_EVEN"])),
    ("A","M17", # PR30A
        FuzzConfig(job="IO2A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R30C87:SYSIO_B2_0_ODD"])),
    ("B","M18", # PR30B
        FuzzConfig(job="IO2B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R30C87:SYSIO_B2_0_ODD"])),
    ("A","T18", # PR46A
        FuzzConfig(job="IC2A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C87:SYSIO_B2_0_C", "CIB_R47C87:SYSIO_B2_0_REM"])),
    ("B","U18", # PR46B
        FuzzConfig(job="IC2B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C87:SYSIO_B2_0_C", "CIB_R47C87:SYSIO_B2_0_REM"])),
    ("A","R3", # PL49A
        FuzzConfig(job="IO6A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R49C0:SYSIO_B6_0_ODD"])),
    ("B","R4", # PL49B
        FuzzConfig(job="IO6B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R49C0:SYSIO_B6_0_ODD"])),
    ("A","L1", # PL27A
        FuzzConfig(job="IO6AE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R27C0:SYSIO_B6_0_EVEN"])),
    ("B","L2", # PL27B
        FuzzConfig(job="IO6BE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R27C0:SYSIO_B6_0_EVEN"])),
    ("A","P5", # PL46A
        FuzzConfig(job="IC6A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C0:SYSIO_B6_0_C", "CIB_R47C0:SYSIO_B6_0_REM"])),
    ("B","P6", # PL46B
        FuzzConfig(job="IC6B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R46C0:SYSIO_B6_0_C", "CIB_R47C0:SYSIO_B6_0_REM"])),
    ("A","E2", # PL15A
        FuzzConfig(job="IO7A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R15C0:SYSIO_B7_0_ODD"])),
    ("B","F1", # PL15B
        FuzzConfig(job="IO7B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R15C0:SYSIO_B7_0_ODD"])),
    ("A","D6", # PL6A
        FuzzConfig(job="IO7AE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C0:SYSIO_B7_0_EVEN"])),
    ("B","D5", # PL6B
        FuzzConfig(job="IO7BE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R6C0:SYSIO_B7_0_EVEN"])),
    ("A","K2", # PL19A
        FuzzConfig(job="IC7A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R19C0:SYSIO_B7_0_C", "CIB_R20C0:SYSIO_B7_0_REM"])),
    ("B","K1", # PL19B
        FuzzConfig(job="IC7B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R19C0:SYSIO_B7_0_C", "CIB_R20C0:SYSIO_B7_0_REM"])),
    ("A","E18", # PT84A
        FuzzConfig(job="IO0A", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C84:SYSIO_B0_0_ODD"])),
    ("B","D17", # PT84B
        FuzzConfig(job="IO0B", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C84:SYSIO_B0_0_ODD"])),
    ("A","E13", # PT78A
        FuzzConfig(job="IO0AE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C78:SYSIO_B0_0_EVEN"])),
    ("B","D13", # PT78B
        FuzzConfig(job="IO0BE", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R0C78:SYSIO_B0_0_EVEN"])),
]

def main():
    def per_config(config):
        pio, site, cfg = config
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "iob_40.v"
        primtype = "SEIO33_CORE"
        def get_bank_vccio(iotype):
            if iotype == "":
                return "3.3"
            iov = iotype[-2:] if iotype[-1].isdigit() else iotype[-3:-1]
            if iov == "10":
                return "1.0"
            return "{}.{}".format(iov[0], iov[1])
        def get_substs(iotype="BIDIR_LVCMOS33", kv=None, vcc=None, tmux="T"):
            iodir, iostd = iotype.split("_", 2) if iotype != "NONE" else ("","")
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
            return dict(cmt="//" if iotype == "NONE" else "",
                pintype=pintype, primtype=primtype, site=site, iotype=iostd, t=t, extra_config=extra_config, vcc=vcc)
        seio_types = [
            "NONE",
            "INPUT_LVCMOS10",
            "INPUT_LVCMOS12", "OUTPUT_LVCMOS12", "BIDIR_LVCMOS12",
            "INPUT_LVCMOS15", "OUTPUT_LVCMOS15", "BIDIR_LVCMOS15",
            "INPUT_LVCMOS18", "OUTPUT_LVCMOS18", "BIDIR_LVCMOS18",
            "INPUT_LVCMOS25", "OUTPUT_LVCMOS25", "BIDIR_LVCMOS25",
            "INPUT_LVCMOS33", "OUTPUT_LVCMOS33", "BIDIR_LVCMOS33",
            "OUTPUT_LVCMOS25D", "OUTPUT_LVCMOS33D"
        ]

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.BASE_TYPE".format(pio), seio_types,
                        lambda x: get_substs(iotype=x), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DRIVE_3V3".format(pio), ["2", "4", "8", "12", "50RS"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DRIVE_2V5".format(pio), ["2", "4", "8", "10", "50RS"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS25", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DRIVE_1V8".format(pio), ["2", "4", "8", "50RS"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS18", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DRIVE_1V5".format(pio), ["2", "4", "8", "12"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS15", kv=("DRIVE", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DRIVE_1V2".format(pio), ["2", "4", "8", "12"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS12", kv=("DRIVE", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.PULLMODE".format(pio), ["NONE", "UP", "DOWN", "KEEPER", "I3C"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("PULLMODE", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.HYSTERESIS_3V3".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("HYSTERESIS", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.HYSTERESIS_2V5".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS25", kv=("HYSTERESIS", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.HYSTERESIS_1V8".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18", kv=("HYSTERESIS", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.HYSTERESIS_1V5".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS15", kv=("HYSTERESIS", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.HYSTERESIS_1V2".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS12", kv=("HYSTERESIS", x)), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.UNDERDRIVE_3V3".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33" if x=="OFF" else "INPUT_LVCMOS25", vcc="3.3"), True)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.UNDERDRIVE_1V8".format(pio), ["ON", "OFF"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18" if x=="OFF" else "INPUT_LVCMOS15", vcc="1.8"), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.CLAMP".format(pio), ["OFF", "ON"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("CLAMP", x)), True)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.DFTDO2DI".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("DFTDO2DI", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.GLITCHFILTER".format(pio), ["OFF", "ON"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("GLITCHFILTER", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.LOOPBKCD2AB".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("LOOPBKCD2AB", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.OPENDRAIN".format(pio), ["OFF", "ON"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("OPENDRAIN", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SLEEPHIGHLEAKAGE".format(pio), ["DISABLED", "ENABLED"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("SLEEPHIGHLEAKAGE", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SLEWRATE".format(pio), ["FAST", "MED", "SLOW"],
                        lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("SLEWRATE", x)), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.TERMINATION_1V8".format(pio), ["OFF", "40", "50", "60", "75", "150"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS18", kv=("TERMINATION", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.TERMINATION_1V5".format(pio), ["OFF", "40", "50", "60", "75"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS15", kv=("TERMINATION", x)), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.TERMINATION_1V2".format(pio), ["OFF", "40", "50", "60", "75"],
                        lambda x: get_substs(iotype="INPUT_LVCMOS12", kv=("TERMINATION", x)), False)

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.TMUX".format(pio), ["T", "INV"],
                        lambda x: get_substs(iotype="BIDIR_LVCMOS33", tmux=x), False)

    fuzzloops.parallel_foreach(configs, per_config)
if __name__ == "__main__":
    main()
