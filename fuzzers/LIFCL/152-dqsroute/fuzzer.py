from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="DQS3", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C75:SYSIO_B3_1_DQS0", "CIB_R56C76:SYSIO_B3_0_DQS1", "CIB_R56C77:SYSIO_B3_1_DQS2", "CIB_R56C78:SYSIO_B3_0_DQS3", "CIB_R56C79:SYSIO_B3_1_DQS4"]),
        "rc": (55, 70),
    },
    {
        "cfg": FuzzConfig(job="DQS4", device="LIFCL-40", sv="../shared/route_40.v",
            tiles=["CIB_R56C21:SYSIO_B4_1_DQS0", "CIB_R56C22:SYSIO_B4_0_DQS1", "CIB_R56C23:SYSIO_B4_1_DQS2", "CIB_R56C24:SYSIO_B4_0_DQS3", "CIB_R56C25:SYSIO_B4_1_DQS4"]),
        "rc": (55, 16),
    },
]

ignore_tiles = set([
    "CIB_R55C{}:CIB".format(i) for i in range(1, 87)
])

def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("DQSBUF_CORE" in x or "DQS_TOP" in x)
        def pip_filter(x, nodes):
            src, snk = x
            return "IOLOGIC_CORE" not in snk and "DDRDLL_CORE" not in src
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True, ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
