from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

cfg = FuzzConfig(job="PLLIP", device="LIFCL-40", sv="../shared/empty_40.v", tiles=["PLL_LLC:PLL_CORE"])

def bin2dec(bits):
    x = 0
    for i, b in enumerate(bits):
        if b:
            x |= (1 << i)
    return x

def bin2bin(bits):
    return "0b{}".format("".join(["1" if b else "0" for b in reversed(bits)]))


def main():
    cfg.setup()
    cfg.sv = "pll.v"
    for o in "ABCDEF":
        nonrouting.fuzz_ip_word_setting(cfg, "DIV" + o, 7, lambda b: dict(k="DIV" + o, v=str(bin2dec(b))), "divider {} minus 1".format(o))
        nonrouting.fuzz_ip_word_setting(cfg, "DEL" + o, 7, lambda b: dict(k="DEL" + o, v=str(bin2dec(b))), "output {} delay in VCO cycles".format(o))
        nonrouting.fuzz_ip_word_setting(cfg, "PHI" + o, 3, lambda b: dict(k="PHI" + o, v=str(bin2dec(b))), "output {} VCO phase shift".format(o))

    gen_settings = [
        ("BW_CTL_BIAS", 4, bin2bin, ""),
        ("CLKOP_TRIM", 4, bin2bin, ""),
        ("CLKOS_TRIM", 4, bin2bin, ""),
        ("CLKOS2_TRIM", 4, bin2bin, ""),
        ("CLKOS3_TRIM", 4, bin2bin, ""),
        ("CLKOS4_TRIM", 4, bin2bin, ""),
        ("CLKOS5_TRIM", 4, bin2bin, ""),
        ("DIV_DEL", 7, bin2bin, ""),
        ("DYN_SEL", 3, bin2bin, ""),
        ("FBK_CUR_BLE", 8, bin2bin, "feedback bleed current control"),
        ("FBK_IF_TIMING_CTL", 2, bin2bin, ""),
        ("FBK_MASK", 8, bin2bin, ""),
        ("FBK_MMD_DIG", 8, bin2dec, ""),
        ("FBK_MMD_PULS_CTL", 4, bin2bin, ""),
        ("FBK_MODE", 2, bin2bin, ""),
        ("FBK_PI_RC", 4, bin2bin, "feedback PI loop RC"),
        ("FBK_PR_CC", 4, bin2bin, "feedback PI loop current"),
        ("FBK_PR_IC", 4, bin2bin, "feedback PI loop bias current"),
        ("FBK_RSV", 16, bin2bin, ""),
        ("IPI_CMP", 4, bin2bin, ""),
        ("IPI_CMPN", 4, bin2bin, ""),
        ("IPP_CTRL", 4, bin2bin, ""),
        ("IPP_SEL", 4, bin2bin, ""),
        ("KP_VCO", 5, bin2bin, "VCO gain setting"),
        ("MFG_CTRL", 4, bin2bin, ""),
        ("MFGOUT1_SEL", 3, bin2bin, ""),
        ("MFGOUT2_SEL", 3, bin2bin, ""),
        ("REF_MASK", 8, bin2bin, ""),
        ("REF_MMD_DIG", 8, bin2dec, ""),
        ("REF_MMD_IN", 8, bin2bin, ""),
        ("REF_MMD_PULS_CTL", 4, bin2bin, ""),
        ("REF_TIMING_CTL", 2, bin2bin, ""),
        ("SSC_DELTA", 15, bin2bin, ""),
        ("SSC_DELTA_CTL", 2, bin2bin, ""),
        ("SSC_F_CODE", 15, bin2bin, ""),
        ("SSC_N_CODE", 9, bin2bin, ""),
        ("SSC_REG_WEIGHTING_SEL", 3, bin2bin, ""),
        ("SSC_STEP_IN", 7, bin2bin, ""),
        ("SSC_TBASE", 12, bin2bin, ""),
        ("V2I_PP_ICTRL", 5, bin2bin, ""),
    ]
    for name, width, conv, desc in gen_settings:
        nonrouting.fuzz_ip_word_setting(cfg, name, width, lambda b: dict(k=name, v=str(conv(b))), desc)

    endis = ["ENABLED", "DISABLED"]
    bypuse = ["BYPASSED", "USED"]

    enum_settings = [
        ("V2I_PP_RES", ["11P3K", "9K", "9P3K", "9P7K", "10K", "10P3K", "10P7K", "11K"], "high frequency pole resistor"),
        ("CRIPPLE", ["{}P".format(c) for c in range(1, 16, 2)], "LPF C<sub>ripple</sub>"),
        ("CSET", ["{}P".format(c) for c in range(8, 69, 4)], "LPF C<sub>set</sub>"),
        ("DELAY_CTRL", ["200PS", "300PS"], "PFD delay control"),
        ("DIRECTION", endis, "VCO direction selection"),
        ("DYN_SOURCE", ["DYNAMIC", "STATIC"], "enable phase shifting from CIB"),
        ("ENCLK_CLKOP", endis, "CLKOP output enable"),
        ("ENCLK_CLKOS", endis, "CLKOS output enable"),
        ("ENCLK_CLKOS2", endis, "CLKOS2 output enable"),
        ("ENCLK_CLKOS3", endis, "CLKOS3 output enable"),
        ("ENCLK_CLKOS4", endis, "CLKOS4 output enable"),
        ("ENCLK_CLKOS5", endis, "CLKOS5 output enable"),
        ("ENABLE_SYNC", endis, "enable synchronous gating of secondary outputs"),
        ("FAST_LOCK_EN", endis, "enable fast lock mode"),
        ("FBK_EDGE_SEL", ["POSITIVE", "NEGATIVE"], "feedback PI output edge select"),
        ("FBK_INTEGER_MODE", endis, "enable integer feedback divider"),
        ("FBK_PI_BYPASS", ["NOT_BYPASSED", "BYPASSED"], "bypass feedback PI section"),
        ("FLOAT_CP", endis, "charge pump output hi-z"),
        ("FLOCK_CTRL", ["1X", "2X", "4X", "8X"], "fast lock period control"),
        ("FLOCK_EN", endis, "enable fast lock"),
        ("FLOCK_SRC_SEL", ["REFCLK", "FBCLK"], "fast lock input source selection"),
        ("FORCE_FILTER", endis, ""),
        ("I_CTRL", ["10UA", "8P3UA", "14P9UA", "12P4UA", "19P8UA", "17P3UA", "24P8UA", "22P3UA"], ""),
        ("IPI_COMP_EN", endis, ""),
        ("LDT_INT_LOCK_STICKY", endis, "enable 'sticky' internal lock"),
        ("LDT_LOCK", ["98304CYC", "24576CYC", "6144CYC", "1536CYC"], "lock detector sensitivity"),
        ("LDT_LOCK_SEL", ["UFREQ", "SPHASE", "SFREQ", "UFREQ_SPHASE", "U_FREQ", "U_PHASE", "S_FREQ", "U_FREQ_S_PHASE"], "lock detector type"),
        ("LEGACY_ATT", endis, ""),
        ("LOAD_REG", endis, "load divider phase control"),
        ("MFG_SEL", ["ICP_UP", "PCP_UP", "IV2I", "PV21", "ICP_DN", "PCP_DN", "RSVD"], ""),
        ("OPENLOOP_EN", endis, ""),
        ("PLLPDN_EN", endis, "enable power down input"),
        ("PLLPD_N", ["USED", "UNUSED"], "enable PLL power"),
        ("PLLRESET_ENA", endis, "enable external reset input"),
        ("REF_INTEGER_MODE", endis, "enable integer reference clock pre-divider"),
        ("REFIN_RESET", ["SET", "RESET"], ""),
        ("RESET_LF", endis, "LPF reset"),
        ("ROTATE", endis, ""),
        ("SEL_OUTA", endis, ""),
        ("SEL_OUTB", endis, ""),
        ("SEL_OUTC", endis, ""),
        ("SEL_OUTD", endis, ""),
        ("SEL_OUTE", endis, ""),
        ("SEL_OUTF", endis, ""),
        ("SLEEP", endis, ""),
        ("SSC_DITHER", endis, ""),
        ("SSC_EN_CENTER_IN", ["DOWN_TRIANGLE", "CENTER_TRIANGLE"], ""),
        ("SSC_EN_SDM", endis, ""),
        ("SSC_EN_SSC", endis, ""),
        ("SSC_ORDER", ["SDM_ORDER2", "SDM_ORDER1"], ""),
        ("SSC_PI_BYPASS", ["NOT_BYPASSED", "BYPASSED"], ""),
        ("SSC_SQUARE_MODE", endis, ""),
        ("STDBY_ATT", endis, "enable standby input"),
        ("TRIMOP_BYPASS_N", bypuse, "bypass CLKOP trimming"),
        ("TRIMOS_BYPASS_N", bypuse, "bypass CLKOS trimming"),
        ("TRIMOS2_BYPASS_N", bypuse, "bypass CLKOS2 trimming"),
        ("TRIMOS3_BYPASS_N", bypuse, "bypass CLKOS3 trimming"),
        ("TRIMOS4_BYPASS_N", bypuse, "bypass CLKOS4 trimming"),
        ("TRIMOS5_BYPASS_N", bypuse, "bypass CLKOS5 trimming"),
        ("V2I_KVCO_SEL", [str(x) for x in range(10, 120, 5)], ""),
        ("V2I_1V_EN", endis, "PLL VCC selection"),
    ]
    empty = cfg.build_design(cfg.sv, dict(k="V2I_PP_RES", v="11P3K"))
    for name, options, desc in enum_settings:
        func = lambda x,name=name: dict(k=name, v=x)
        if name == "V2I_KVCO_SEL":
            cfg.sv = "pll_2.v"
            empty = cfg.build_design(cfg.sv, dict(k="V2I_PP_RES", v="11P3K", ldt="LDT_LOCK_SEL", ldt_val="U_FREQ"))
            func = lambda x,name=name: dict(k=name, v=x, ldt="LDT_LOCK_SEL", ldt_val="U_FREQ")
        nonrouting.fuzz_ip_enum_setting(cfg, empty, name, options, func, desc)
        if name == "V2I_KVCO_SEL":
            cfg.sv = "pll.v"
            empty = cfg.build_design(cfg.sv, dict(k="V2I_PP_RES", v="11P3K"))
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)
