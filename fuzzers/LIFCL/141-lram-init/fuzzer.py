from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="LRAMINIT", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["LRAM_CORE_R18C86:LRAM_INIT"])

def bin2dec(bits):
    x = 0
    for i, b in enumerate(bits):
        if b:
            x |= (1 << i)
    return x

def main():
    cfg.setup()
    cfg.sv = "lram.v"
    def per_word(w):
        nonrouting.fuzz_ip_word_setting(cfg, "INITVAL_{:02X}".format(w), 5120, lambda b: dict(a="{:02X}".format(w), v="0x{:01280x}".format(bin2dec(b))))
    # Only fuzz a couple of init values to stop the database getting massive - we can derive the rest
    fuzzloops.parallel_foreach(range(0x2), per_word)
if __name__ == "__main__":
    main()
