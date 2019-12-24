from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="REGCFG", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R8C87:SYSIO_B1_0"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "iob_40.v"
    site = "F16" # PR8A
    primtype = "SEIO33_CORE"
    def get_bank_vccio(iotype):
        if iotype == "":
            return "3.3"
        iov = iotype[-2:]
        if iov == "10":
            return "1.0"
        return "{}.{}".format(iov[0], iov[1])
    def get_substs(iotype="BIDIR_LVCMOS33", kv=None, vcc=None):
        iodir, iostd = iotype.split("_", 2) if iotype != "NONE" else ("","")
        if iodir == "INPUT":
            pintype = "input"
            t = "1"
        elif iodir == "OUTPUT":
            pintype = "output"
            t = "0"
        else:
            pintype = "inout"
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

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.BASE_TYPE", seio_types,
                    lambda x: get_substs(iotype=x), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DRIVE_3V3", ["2", "4", "8", "12", "50RS"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("DRIVE", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DRIVE_2V5", ["2", "4", "8", "10", "50RS"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS25", kv=("DRIVE", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DRIVE_1V8", ["2", "4", "8", "50RS"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS18", kv=("DRIVE", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DRIVE_1V5", ["2", "4", "8", "12"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS15", kv=("DRIVE", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DRIVE_1V2", ["2", "4", "8", "12"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS12", kv=("DRIVE", x)), True)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.PULLMODE", ["NONE", "UP", "DOWN", "KEEPER", "I3C"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("PULLMODE", x)), True)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.HYSTERESIS_3V3", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("HYSTERESIS", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.HYSTERESIS_2V5", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS25", kv=("HYSTERESIS", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.HYSTERESIS_1V8", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS18", kv=("HYSTERESIS", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.HYSTERESIS_1V5", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS15", kv=("HYSTERESIS", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.HYSTERESIS_1V2", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS12", kv=("HYSTERESIS", x)), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.UNDERDRIVE_3V3", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33" if x=="OFF" else "INPUT_LVCMOS25", vcc="3.3"), True)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.UNDERDRIVE_1V8", ["ON", "OFF"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS18" if x=="OFF" else "INPUT_LVCMOS15", vcc="1.8"), True)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.CLAMP", ["OFF", "ON"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("PULLMODE", x)), True)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.DFTDO2DI", ["DISABLED", "ENABLED"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("DFTDO2DI", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.GLITCHFILTER", ["OFF", "ON"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("GLITCHFILTER", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.LOOPBKCD2AB", ["DISABLED", "ENABLED"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("LOOPBKCD2AB", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.OPENDRAIN", ["OFF", "ON"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("OPENDRAIN", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.SLEEPHIGHLEAKAGE", ["DISABLED", "ENABLED"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS33", kv=("SLEEPHIGHLEAKAGE", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.SLEWRATE", ["FAST", "MED", "SLOW"],
                    lambda x: get_substs(iotype="OUTPUT_LVCMOS33", kv=("SLEWRATE", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.TERMINATION_1V8", ["OFF", "40", "50", "60", "75", "150"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS18", kv=("TERMINATION", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.TERMINATION_1V5", ["OFF", "40", "50", "60", "75"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS15", kv=("TERMINATION", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "IOB_A.TERMINATION_1V2", ["OFF", "40", "50", "60", "75"],
                    lambda x: get_substs(iotype="INPUT_LVCMOS12", kv=("TERMINATION", x)), False)

if __name__ == "__main__":
    main()
