from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="EBRINIT", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["EBR_WID0:EBR_INIT"])

def bin2dec(bits):
    x = 0
    for i, b in enumerate(bits):
        if b:
            x |= (1 << i)
    return x

def main():
    cfg.setup()
    cfg.sv = "ebr.v"
    def per_word(w):
        nonrouting.fuzz_ip_word_setting(cfg, "INITVAL_{:02X}".format(w), 320, lambda b: dict(a="{:02X}".format(w), v="0x{:080x}".format(bin2dec(b))))
    fuzzloops.parallel_foreach(range(0x40), per_word)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
