import asyncio

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

async def main(executor):
    cfg.setup()
    cfg.sv = "lram.v"
    async def per_word(w):
        await fuzzloops.wrap_future(nonrouting.fuzz_ip_word_setting(cfg, "INITVAL_{:02X}".format(w), 5120,
                                                                    lambda b: dict(a="{:02X}".format(w), v="0x{:01280x}".format(bin2dec(b))), executor=executor))
    # Only fuzz a couple of init values to stop the database getting massive - we can derive the rest
    await asyncio.gather(*[per_word(w) for w in range(0x02)])
if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(main)
