import asyncio

from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="PLCINIT", device="LIFCL-40", tiles=["R2C2:PLC"])

def get_lut_function(init_bits):
    sop_terms = []
    lut_inputs = ["A", "B", "C", "D"]
    for i in range(16):
        if init_bits[i]:
            p_terms = []
            for j in range(4):
                if i & (1 << j) != 0:
                    p_terms.append(lut_inputs[j])
                else:
                    p_terms.append("~" + lut_inputs[j])
            sop_terms.append("({})".format("*".join(p_terms)))
    if len(sop_terms) == 0:
        lut_func = "0"
    else:
        lut_func = "+".join(sop_terms)
    return lut_func


async def main(executor):
    cfg.setup()
    cfg.sv = "lut.v"

    async def per_slice(slicen):
        for k in range(2):
            await asyncio.wrap_future(executor.submit(nonrouting.fuzz_word_setting, cfg, "SLICE{}.K{}.INIT".format(slicen, k), 16,
                                                      lambda  bits, k=k,slicen=slicen: dict(z=slicen, k=str(k), func=get_lut_function(bits)),
                desc="SLICE {} LUT{} init value".format(slicen, k), executor=executor))

    await asyncio.gather(*[per_slice(s) for s in ["A", "B", "C", "D"]])

if __name__ == "__main__":
    fuzzloops.FuzzerAsyncMain(main)
