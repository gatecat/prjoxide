from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="SYSCONFIG", device="LIFCL-40", sv="../shared/empty_40.v",
    tiles=["CIB_R0C75:EFB_0", "CIB_R0C72:BANKREF0", "CIB_R0C77:EFB_1_OSC", "CIB_R0C79:EFB_2",
    "CIB_R0C81:I2C_EFB_3", "CIB_R0C85:PMU", "CIB_R0C87:MIB_CNR_32_FAFD", "CIB_R1C87:IREF_P33", "CIB_R2C87:POR"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "../shared/empty_presyn_40.v"
    cfg.struct_mode = False
    def get_substs(k, v):
        return dict(sysconfig="{}={}".format(k, v))
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.MASTER_SPI_PORT", ["DISABLE", "SERIAL", "DUAL", "QUAD"],
                            lambda x: get_substs("MASTER_SPI_PORT", x), False,
                            assume_zero_base=True,
                            desc="status of master SPI port after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.SLAVE_SPI_PORT", ["DISABLE", "SERIAL", "DUAL", "QUAD"],
                            lambda x: get_substs("SLAVE_SPI_PORT", x), False,
                            assume_zero_base=True,
                            desc="status of slave SPI port after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.SLAVE_I2CI3C_PORT", ["DISABLE", "ENABLE"],
                            lambda x: get_substs("SLAVE_I2CI3C_PORT", x), False,
                            assume_zero_base=True,
                            desc="status of slave I2C/I3C port after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.JTAG_PORT", ["DISABLE", "ENABLE"],
                            lambda x: get_substs("JTAG_PORT", x), False,
                            assume_zero_base=True,
                            desc="status of JTAG port after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.DONE_PORT", ["DISABLE", "ENABLE"],
                            lambda x: get_substs("DONE_PORT", x), False,
                            assume_zero_base=True,
                            desc="use DONE output after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.INITN_PORT", ["DISABLE", "ENABLE"],
                            lambda x: get_substs("INITN_PORT", x), False,
                            assume_zero_base=True,
                            desc="use INITN input after configuration")
    nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.PROGRAMN_PORT", ["DISABLE", "ENABLE"],
                            lambda x: get_substs("PROGRAMN_PORT", x), False,
                            assume_zero_base=True,
                            desc="use PROGRAMN input after configuration")
if __name__ == "__main__":
    main()
