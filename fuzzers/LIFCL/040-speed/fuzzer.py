from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import database

speed_map = {
	"SLOW_1V0": "7_High-Performance_1.0V",
	"FAST_1V0": "7_Low-Power_1.0V",
}

all_tiles_40 = set(database.get_tilegrid("LIFCL", "LIFCL-40")["tiles"].keys())

cfg = FuzzConfig(job="SPEED", device="LIFCL-40", sv="../shared/empty_40.v", tiles=all_tiles_40)
#cfg = FuzzConfig(job="SPEED", device="LIFCL-40", sv="../shared/empty_40.v", tiles=set(["CIB_R43C0:RBB_12"]))


def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "speed_40.v"
    nonrouting.fuzz_enum_setting(cfg, empty, "CHIP.SPEED", ["SLOW_1V0", "FAST_1V0"],
            lambda x: {"speed": speed_map[x]}, True)
if __name__ == "__main__":
    main()
