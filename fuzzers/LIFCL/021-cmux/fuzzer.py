from fuzzconfig import FuzzConfig
from interconnect import fuzz_interconnect
import re

cfg = FuzzConfig(job="CMUXROUTE", device="LIFCL-40", sv="../shared/route_40.v", tiles=["CIB_R29C49:CMUX_0", "CIB_R29C50:CMUX_1", "CIB_R38C49:CMUX_2", "CIB_R38C50:CMUX_3"])

def main():
    cfg.setup()
    nodes = ["R28C49_JHPRX{}_CMUX_CORE_CMUX1".format(i) for i in range(16)] + \
            ["R28C49_JHPRX{}_CMUX_CORE_CMUX0".format(i) for i in range(16)] + \
            ["R28C49_JDCSMUXOUT_DCSMUX_CORE_DCSMUX0", "R28C49_JDCSMUXOUT_DCSMUX_CORE_DCSMUX1"]
    fuzz_interconnect(config=cfg, nodenames=nodes, regex=False, bidir=False, full_mux_style=True)
    misc_nodes = []
    for i in range(4):
        misc_nodes.append("R28C49_JCLKI_DCC_DCC{}".format(i))
        misc_nodes.append("R28C49_JCE_DCC_DCC{}".format(i))
        misc_nodes.append("R28C49_JCLKO_DCC_DCC{}".format(i))
    for q in ("UL", "UR", "LL", "LR"):
        misc_nodes.append("R28C49_JJCLK{}_CMUX_CORE_CMUX0".format(q))
        misc_nodes.append("R28C49_JJCLK{}_CMUX_CORE_CMUX1".format(q))
        misc_nodes.append("R28C49_JJCLK{}_DCSMUX_CORE_DCSMUX0".format(q))
        misc_nodes.append("R28C49_JJCLK{}_DCSMUX_CORE_DCSMUX1".format(q))
    misc_nodes.append("R28C49_JCLK0_DCS_DCSIP")
    misc_nodes.append("R28C49_JCLK1_DCS_DCSIP")
    misc_nodes.append("R28C49_JDCS0_CMUX_CORE_CMUX0")
    misc_nodes.append("R28C49_JDCS0_CMUX_CORE_CMUX1")
    misc_nodes.append("R28C49_JDCSOUT_DCS_DCSIP")
    misc_nodes.append("R28C49_JSEL_DCS_DCSIP")
    misc_nodes.append("R28C49_JSELFORCE_DCS_DCSIP")

    misc_nodes.append("R28C49_JCLKOUT_PCLKDIV_PCLKDIV")
    misc_nodes.append("R28C49_JLSRPDIV_PCLKDIV_PCLKDIV")
    for i in range(3):
        misc_nodes.append("R28C49_JPCLKDIVTESTINP{}_PCLKDIV_PCLKDIV".format(i))
    misc_nodes.append("R28C49_JCLKIN_PCLKDIV_PCLKDIV")

    for i in range(2):
        for j in range(7):
            misc_nodes.append("R28C49_JTESTINP{}_DCSMUX_CORE_DCSMUX{}".format(j, i))
        for j in range(5):
            misc_nodes.append("R28C49_JTESTINP{}_CMUX_CORE_CMUX{}".format(j, i))
    misc_nodes.append("R28C49_JGSR_N_GSR_CORE_GSR_CENTER")
    misc_nodes.append("R28C49_JCLK_GSR_CORE_GSR_CENTER")
    fuzz_interconnect(config=cfg, nodenames=misc_nodes, regex=False, bidir=False, full_mux_style=False)
if __name__ == "__main__":
    main()
