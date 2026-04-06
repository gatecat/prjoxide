from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

import os
import get_params


cfg = FuzzConfig(job="DPHYIP", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["TDPHY_CORE2:DPHY_CORE"])

def bin2bin(bits):
    return "0b{}".format("".join(["1" if b else "0" for b in reversed(bits)]))


def main():
    cfg.setup()
    cfg.sv = "dphy.v"
    empty = cfg.build_design(cfg.sv, dict(k="GSR", v="ENABLED"))
    words, enums = get_params.get_params(os.path.join(os.environ['RADIANTDIR'], "cae_library", "simulation", "verilog", "lifcl", "DPHY.v"))
    def per_word(w):
        name, width, default = w
        nonrouting.fuzz_ip_word_setting(cfg, name, width, lambda b: dict(k=name, v=str(bin2bin(b))), "")
    fuzzloops.parallel_foreach(words, per_word)
    def per_enum(e):
        name, options = e
        nonrouting.fuzz_ip_enum_setting(cfg, empty, name, options, lambda x: dict(k=name, v=x), "")
    fuzzloops.parallel_foreach(enums, per_enum)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

