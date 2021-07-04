from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="CMUXROUTE", device="LFCPNX-100", sv="../shared/route_100.v",
    tiles=["CIB_R38C73:CMUX_0", "CIB_R38C74:CMUX_1_GSR",
    "CIB_R47C73:CMUX_2_TRUNK_LL", "CIB_R47C74:CMUX_3_TRUNK_LR",
    "CIB_R29C73:CMUX_4_TRUNK_UL", "CIB_R29C74:CMUX_5_TRUNK_UR",
    "CIB_R56C73:CMUX_6", "CIB_R56C74:CMUX_7"])

def main():
    cfg.setup()
    nodes = ["R37C73_JHPRX{}_CMUX_CORE_CMUX3".format(i) for i in range(16)] + \
            ["R37C73_JHPRX{}_CMUX_CORE_CMUX2".format(i) for i in range(16)] + \
            ["R37C73_JHPRX{}_CMUX_CORE_CMUX1".format(i) for i in range(16)] + \
            ["R37C73_JHPRX{}_CMUX_CORE_CMUX0".format(i) for i in range(16)] + \
            ["R37C73_JDCSMUXOUT_DCSMUX_CORE_DCSMUX{}".format(i) for i in range(4)]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=True)
    misc_nodes = []
    for i in range(4):
        misc_nodes.append("R37C73_JCLKI_DCC_DCC{}".format(i))
        misc_nodes.append("R37C73_JCE_DCC_DCC{}".format(i))
        misc_nodes.append("R37C73_JCLKO_DCC_DCC{}".format(i))
    for q in ("UL", "UR", "LL", "LR"):
        for i in range(4):
            misc_nodes.append(f"R37C73_JJCLK{q}_CMUX_CORE_CMUX{i}")
            misc_nodes.append(f"R37C73_JJCLK{q}_DCSMUX_CORE_DCSMUX{i}")
    for i in range(4):
        misc_nodes.append(f"R37C73_JCLK0_DCS_DCSIP{i}")
        misc_nodes.append(f"R37C73_JCLK1_DCS_DCSIP{i}")
        misc_nodes.append(f"R37C73_JDCS{i}_CMUX_CORE_CMUX0")
        misc_nodes.append(f"R37C73_JDCS{i}_CMUX_CORE_CMUX1")
        misc_nodes.append(f"R37C73_JDCS{i}_CMUX_CORE_CMUX2")
        misc_nodes.append(f"R37C73_JDCS{i}_CMUX_CORE_CMUX3")
        misc_nodes.append(f"R37C73_JDCSOUT_DCS_DCSIP{i}")
        misc_nodes.append(f"R37C73_JSEL_DCS_DCSIP{i}")
        misc_nodes.append(f"R37C73_JSELFORCE_DCS_DCSIP{i}")
    for i in range(2):
        misc_nodes.append(f"R37C73_JCLKOUT_PCLKDIV_PCLKDIV{i}")
        misc_nodes.append(f"R37C73_JLSRPDIV_PCLKDIV_PCLKDIV{i}")
        for j in range(3):
            misc_nodes.append(f"R37C73_JPCLKDIVTESTINP{j}_PCLKDIV_PCLKDIV{i}")
        misc_nodes.append(f"R37C73_JCLKIN_PCLKDIV_PCLKDIV{i}")

    for i in range(4):
        for j in range(7):
            misc_nodes.append("R37C73_JTESTINP{}_DCSMUX_CORE_DCSMUX{}".format(j, i))
        for j in range(5):
            misc_nodes.append("R37C73_JTESTINP{}_CMUX_CORE_CMUX{}".format(j, i))
    misc_nodes.append("R37C73_JGSR_N_GSR_CORE_GSR_CENTER")
    misc_nodes.append("R37C73_JCLK_GSR_CORE_GSR_CENTER")
    fuzz_interconnect(config=cfg, nodenames=misc_nodes, regex=False, bidir=False, full_mux_style=False)
if __name__ == "__main__":
    main()
