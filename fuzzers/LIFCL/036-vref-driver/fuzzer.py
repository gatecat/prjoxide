from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

configs = [
    ("A","U1", 1, # PB4A
        FuzzConfig(job="VREF5_1", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C4:SYSIO_B5_0"])),
    ("B","W5", 2, # PB12B
        FuzzConfig(job="VREF5_2", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C13:SYSIO_B5_1_V18"])),

    ("A","T6", 1, # PB16A
        FuzzConfig(job="VREF4_1", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C16:SYSIO_B4_0"])),
    ("B","R11", 2, # PB46B
        FuzzConfig(job="VREF4_2", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C47:SYSIO_B4_1"])),

    ("A","W11", 1, # PB54A
        FuzzConfig(job="VREF3_1", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C54:SYSIO_B3_0_DLY30_V18"])),
    ("B","Y18", 2, # PB84B
        FuzzConfig(job="VREF3_2", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["CIB_R56C85:SYSIO_B3_1_V18"])),
]

def main():
    def per_config(config):
        pio, site, vref, cfg = config
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

        def get_substs(iotype="NONE", vcc="1.5"):
            primtype = "SEIO18_CORE"
            return dict(cmt="//" if iotype == "NONE" else "",
                pintype="input", primtype=primtype, site=site, iotype=iotype, extra_config="", vcc=vcc, t="1")

        nonrouting.fuzz_enum_setting(cfg, empty, "PIO{}.SEIO18.VREF{}_DRIVER".format(pio, vref), ["OFF", "ON"],
                lambda x: get_substs(iotype=f"VREF{vref}_DRIVER" if x == "ON" else "NONE"), False, assume_zero_base=False)

    fuzzloops.parallel_foreach(configs, per_config)
if __name__ == "__main__":
    main()
