from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

import os
import get_params


cfg = FuzzConfig(job="PCIEIP", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["TPCIE_CORE57:PCIE_CORE"])

def bin2bin(bits):
    return "0b{}".format("".join(["1" if b else "0" for b in reversed(bits)]))

defaults = []

def get_substs(k, v):
    p = "{}={}".format(k, v)
    for dk, dv in defaults:
        if dk != k:
            p += ",{}={}".format(dk, dv)
    return dict(p=p)

def main():
    cfg.setup()
    cfg.sv = "pcie.v"
    empty = cfg.build_design(cfg.sv, get_substs("GSR", "ENABLED"))
    words, enums = get_params.get_params(os.path.join(os.environ['RADIANTDIR'], "cae_library", "simulation", "verilog", "lifcl", "PCIE.v"))
    # force words with non-zero default to zero...
    for n, w, d in words:
        if int(d, 2) != 0:
            defaults.append((n, "0b{}".format("0" * w)))
    def per_word(w):
        name, width, default = w
        nonrouting.fuzz_ip_word_setting(cfg, name, width, lambda b: get_substs(name, str(bin2bin(b))), "", default=[d == "1" for d in reversed(default)])
    fuzzloops.parallel_foreach(words, per_word)
    def per_enum(e):
       name, options = e
       nonrouting.fuzz_ip_enum_setting(cfg, empty, name, options, lambda x: get_substs(name, x), "")
    fuzzloops.parallel_foreach(enums, per_enum)

if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

