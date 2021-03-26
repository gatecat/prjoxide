from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import libpyprjoxide
import fuzzconfig

cfgs = [
	FuzzConfig(job="EMPTY", device="LIFCL-40", sv="../shared/empty_40.v", tiles=[]),
	FuzzConfig(job="EMPTY", device="LIFCL-17", sv="../shared/empty_17.v", tiles=[]),
]

def main():
	for cfg in cfgs:
	    cfg.setup()
	    empty = cfg.build_design(cfg.sv, {})
	    libpyprjoxide.add_always_on_bits(fuzzconfig.db, empty)

if __name__ == "__main__":
    main()
