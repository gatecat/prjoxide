from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

configs = [
    {
        "cfg": FuzzConfig(job="IOROUTE5", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R74C10:SYSIO_B5_0", "CIB_R74C11:SYSIO_B5_1"]),
        "rc": (74, 10),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE4", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R74C58:SYSIO_B4_0", "CIB_R74C59:SYSIO_B4_1"]),
        "rc": (74, 58),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE3", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R74C118:SYSIO_B3_0", "CIB_R74C119:SYSIO_B3_1"]),
        "rc": (74, 118),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE2E", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R44C159:SYSIO_B2_0_EVEN"]),
        "rc": (44, 159),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE2O", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R42C159:SYSIO_B2_0_ODD"]),
        "rc": (42, 159),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE1O", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R8C159:SYSIO_B1_0_ODD"]),
        "rc": (8, 159),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE1E", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R6C159:SYSIO_B1_0_EVEN"]),
        "rc": (6, 159),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE0O", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R0C140:SYSIO_B0_0_ODD"]),
        "rc": (0, 140),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE0E", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R0C142:SYSIO_B0_0_EVEN"]),
        "rc": (0, 142),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE7E", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R3C0:SYSIO_B7_0_EVEN"]),
        "rc": (3, 0),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE7O", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R4C0:SYSIO_B7_0_ODD"]),
        "rc": (4, 0),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE6O", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R49C0:SYSIO_B6_0_ODD"]),
        "rc": (49, 0),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE6E", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R44C0:SYSIO_B6_0_EVEN"]),
        "rc": (44, 0),
    },
    {
        "cfg": FuzzConfig(job="IOROUTE1D", device="LFCPNX-100", sv="../shared/route_100.v", tiles=["CIB_R3C159:SYSIO_B1_DED"]),
        "rc": (3, 159),
    },
]

ignore_tiles = set([
    "CIB_R{}C1:CIB_LR".format(c) for c in range(2, 74)
] + [
    "CIB_R{}C158:CIB_LR".format(c) for c in range(2, 74)
] + [
    "CIB_R1C{}:CIB_T".format(c) for c in range(1, 159)
] + [
    "CIB_R73C{}:CIB".format(c) for c in range(1, 159)
] + [
    "CIB_R10C1:CIB_LR_A",
    "CIB_R19C1:CIB_LR_A",
    "CIB_R28C1:CIB_LR_A",
    "CIB_R37C1:CIB_LR_A",
    "CIB_R46C1:CIB_LR_A",
    "CIB_R55C1:CIB_LR_A",
    "CIB_R64C1:CIB_LR_A",
    "CIB_R10C158:CIB_LR_A",
    "CIB_R19C158:CIB_LR_A",
    "CIB_R28C158:CIB_LR_A",
    "CIB_R37C158:CIB_LR_A",
    "CIB_R46C158:CIB_LR_A",
    "CIB_R55C158:CIB_LR_A",
    "CIB_R64C158:CIB_LR_A",
])


def main():
    for config in configs:
        cfg = config["cfg"]
        cfg.setup()
        r, c = config["rc"]
        nodes = ["R{}C{}_*".format(r, c)]
        def nodename_filter(x, nodes):
            return ("R{}C{}_".format(r, c) in x) and ("_GEARING_PIC_TOP_" in x or "SEIO18_CORE" in x or "DIFFIO18_CORE" in x or "I217" in x or "I218" in x or "SEIO33_CORE" in x or "SIOLOGIC_CORE" in x)
        def pip_filter(pip, nodes):
            from_wire, to_wire = pip
            return not ("ADC_CORE" in to_wire or "ECLKBANK_CORE" in to_wire or "MID_CORE" in to_wire
                or "REFMUX_CORE" in to_wire or "CONFIG_JTAG_CORE" in to_wire or "CONFIG_JTAG_CORE" in from_wire
                or "REFCLOCK_MUX_CORE" in to_wire)
        fuzz_interconnect(config=cfg, nodenames=nodes, nodename_predicate=nodename_filter, pip_predicate=pip_filter, regex=True, bidir=True,
            ignore_tiles=ignore_tiles)

if __name__ == "__main__":
    main()
