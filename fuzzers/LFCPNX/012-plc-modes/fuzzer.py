from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="SLICEMODE", device="LFCPNX-100", sv="../shared/empty_100.v", tiles=["R2C2:PLC"])

def main():
    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "slice.v"

    def per_slice(slicen):
        def get_substs(mode="LOGIC", kv=None):
            if kv is None:
                config = ""
            else:
                config = "{}:::{}={}".format(mode, kv[0], kv[1])
            return dict(z=slicen, mode=mode, config=config)
        modes = ["LOGIC", "CCU2"]
        if slicen in ("A", "B"):
            modes.append("DPRAM")
        if slicen == "C":
            modes.append("RAMW")
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.MODE".format(slicen), modes,
            lambda x: get_substs(x), False)
        nonrouting.fuzz_enum_setting(cfg, empty, "SLICE{}.CCU2.INJECT".format(slicen), ["YES", "NO"],
            lambda x: get_substs("CCU2", ("INJECT", x)), False)
    fuzzloops.parallel_foreach(["A", "B", "C", "D"], per_slice)

if __name__ == "__main__":
    main()
