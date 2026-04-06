from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import libpyprjoxide
import fuzzconfig

cfgs = [
	FuzzConfig(job="EMPTY", device="LIFCL-40", sv="../shared/empty_40.v", tiles=[]),
	FuzzConfig(job="EMPTY", device="LIFCL-17", sv="../shared/empty_17.v", tiles=[]),
	FuzzConfig(job="EMPTY", device="LIFCL-33", sv="../shared/empty_33.v", tiles=[]),
]

def main():
    with fuzzconfig.db_lock() as db:
        for cfg in cfgs:
            cfg.setup()
            empty = cfg.build_design(cfg.sv, {})
            libpyprjoxide.add_always_on_bits(db, empty.bitstream)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

