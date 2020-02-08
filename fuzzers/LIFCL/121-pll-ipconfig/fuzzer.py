from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="PLLIP", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["PLL_LLC:PLL_CORE"])

def bin_to_dec(bits):
    x = 0
    for i, b in enumerate(bits):
        if b:
            x |= (1 << i)
    return x

def main():
    cfg.setup()
    cfg.sv = "pll.v"
    nonrouting.fuzz_ip_word_setting(cfg, "DIVA", 7, lambda b: dict(diva=str(bin_to_dec(b))), "divider A minus 1")

if __name__ == "__main__":
    main()
