from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfgs = [
    FuzzConfig(job="SYSCONFIG40", device="LIFCL-40", sv="../shared/empty_40.v",
        tiles=["CIB_R0C75:EFB_0", "CIB_R0C72:BANKREF0", "CIB_R0C77:EFB_1_OSC", "CIB_R0C79:EFB_2",
        "CIB_R0C81:I2C_EFB_3", "CIB_R0C85:PMU", "CIB_R0C87:MIB_CNR_32_FAFD", "CIB_R1C87:IREF_P33", "CIB_R2C87:POR"]),
    FuzzConfig(job="SYSCONFIG17", device="LIFCL-17", sv="../shared/empty_17.v",
        tiles=["CIB_R1C75:IREF_15K", "CIB_R0C75:PPT_QOUT_15K", "CIB_R0C74:PVTCAL33_15K", "CIB_R0C73:POR_15K",
        "CIB_R0C72:I2C_15K", "CIB_R0C71:OSC_15K", "CIB_R0C70:PMU_15K", "CIB_R0C66:EFB_15K"])
]

def main(executor):
    for cfg in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "../shared/empty_presyn_40.v"
        cfg.struct_mode = False
        def get_substs(k, v):
            return dict(sysconfig="{}={}".format(k, v))
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.MASTER_SPI_PORT", ["DISABLE", "SERIAL", "DUAL", "QUAD"],
                                lambda x: get_substs("MASTER_SPI_PORT", x), False,
                                assume_zero_base=True,
                                desc="status of master SPI port after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.SLAVE_SPI_PORT", ["DISABLE", "SERIAL", "DUAL", "QUAD"],
                                lambda x: get_substs("SLAVE_SPI_PORT", x), False,
                                assume_zero_base=True,
                                desc="status of slave SPI port after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.SLAVE_I2C_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("SLAVE_I2C_PORT", x), False,
                                assume_zero_base=True,
                                desc="status of slave I2C port after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.SLAVE_I3C_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("SLAVE_I3C_PORT", x), False,
                                assume_zero_base=True,
                                desc="status of slave I3C port after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.JTAG_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("JTAG_PORT", x), False,
                                assume_zero_base=True,
                                desc="status of JTAG port after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.DONE_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("DONE_PORT", x), False,
                                assume_zero_base=True,
                                desc="use DONE output after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.INITN_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("INITN_PORT", x), False,
                                assume_zero_base=True,
                                desc="use INITN input after configuration",executor=executor)
        nonrouting.fuzz_enum_setting(cfg, empty, "SYSCONFIG.PROGRAMN_PORT", ["DISABLE", "ENABLE"],
                                lambda x: get_substs("PROGRAMN_PORT", x), False,
                                assume_zero_base=True,
                                desc="use PROGRAMN input after configuration",executor=executor)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
