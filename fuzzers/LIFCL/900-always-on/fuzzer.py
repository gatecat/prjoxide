from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re
import libprjoxide
import fuzzconfig

cfg = FuzzConfig(job="EMPTY", device="LIFCL-40", sv="../shared/empty_40.v", tiles=[])


def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    libprjoxide.add_always_on_bits(fuzzconfig.db, empty)

if __name__ == "__main__":
    main()
