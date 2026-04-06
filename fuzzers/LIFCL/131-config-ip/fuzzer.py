from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
import re

settings = {
    "CONFIG_MULTIBOOT_CORE": [
        ("SOURCESEL", ["DIS", "EN"], "selects next address from input pins or fixed parameter")
    ],
    "CONFIG_CLKRST_CORE": [
        ("MCJTAGGSRNDIS", ["DIS", "EN"], ""),
        ("MCLMMIGSRNDIS", ["DIS", "EN"], ""),
        ("MCSEDCGSRNDIS", ["DIS", "EN"], ""),
        ("MCWDTGSRNDIS", ["DIS", "EN"], ""),
        ("MCLMMIGSRNDIS", ["DIS", "EN"], ""),
    ],
    "CONFIG_HSE_CORE": [
        ("MCHSEDISABLE", ["DIS", "EN"], ""),
        ("MCASFCLKINV", ["NINV", "INV"], ""),
        ("MCHSELMMICLKINV", ["NINV", "INV"], "invert HSE LMMICLK"),
    ],
    "CONFIG_CRE_CORE": [
        ("MCHSEDISABLE", ["DIS", "EN"], ""),
        ("MCASFCLKINV", ["NINV", "INV"], ""),
        ("MCHSELMMICLKINV", ["NINV", "INV"], "invert HSE LMMICLK"),
    ],
    "CONFIG_IP_CORE": [
        ("DONEPHASE", ["DIS", "EN"], "changes point at which DONE is asserted during startup"),
        ("MCCIBINT", ["DIS", "EN"], ""),
        ("MCPERSISTUI2C", ["DIS", "EN"], "keep user I2C open after configuration"),
        ("MCUCLKSEL", ["DIS", "EN"], ""),
        ("MCUI2CAFWKUP", ["DIS", "EN"], ""),
        ("PERSISTI2C", ["DIS", "EN"], "keep I2C open after configuration"),
        ("PERSISTI3C", ["DIS", "EN"], "keep I3C open after configuration"),
        ("PERSISTMQUAD", ["DIS", "EN"], "keep master QSPI open after configuration"),
        ("PERSISTMSPI", ["DIS", "EN"], "keep master SPI open after configuration"),
        ("PERSISTSHEXA", ["DIS", "EN"], "keep slave 16-bit 'SPI' open after configuration"),
        ("PERSISTSOCTA", ["DIS", "EN"], "keep slave 8-bit 'SPI' open after configuration"),
        ("PERSISTSQUAD", ["DIS", "EN"], "keep slave QSPI open after configuration"),
        ("PERSISTSSPI", ["DIS", "EN"], "keep slave SPI open after configuration"),
        ("PERSISTWKUP", ["DIS", "EN"], ""),
        ("SCANEN", ["DIS", "EN"], ""),
        ("TRANECI", ["DIS", "EN"], ""),
        ("TRANFIO", ["DIS", "EN"], ""),
        ("TRANGOE", ["DIS", "EN"], ""),
        ("TRANGSRN", ["DIS", "EN"], ""),
        ("TRANGWE", ["DIS", "EN"], ""),
        ("TRANHSE", ["DIS", "EN"], ""),
        ("TRANSBI", ["DIS", "EN"], ""),
        ("WLSLEW", ["DIS", "EN"], ""),
        ("ENTSALL", ["DIS", "EN"], ""),
        ("MCCFGUSEREN", ["DIS", "EN"], ""),
        ("MCJTAGDISABLE", ["DIS", "EN"], ""),
        ("SYNCEXTDONE", ["DIS", "EN"], ""),
        ("TSALLINV", ["NINV", "INV"], ""),
    ],
    "CONFIG_LMMI_CORE": [
        ("LMMI_EN", ["DIS", "EN"], "enable LMMI access to configuration"),
        ("MCLMMICLKINV", ["NINV", "INV"], "invert LMMICLK")
    ],
    "CONFIG_WDT_CORE": [
        ("WDTEN", ["DIS", "EN"], "enable watchdog timer"),
        ("WDTMODE", ["SINGLE", "CONTINUOUS"], "watchdog timer mode"),
    ]
}

words = {
    "CONFIG_MULTIBOOT_CORE": [("MSPIADDR", 32, "SPI flash fixed next address")],
    "CONFIG_IP_CORE": [
        ("DSRFCTRL", 2, ""),
        ("PPTQOUT", 4, ""),
    ],
    "CONFIG_WDT_CORE": [
        ("WDTVALUE", 18, "watchdog timer timeout count")
    ]
}

cfgs = [
    (FuzzConfig(job="CONFIGIP", device="LIFCL-40", sv="../shared/empty_40.v",
        tiles=["CIB_R0C75:EFB_0", "CIB_R0C77:EFB_1_OSC", "CIB_R0C79:EFB_2", "CIB_R0C81:I2C_EFB_3"]),
        [
            ("TCONFIG_WDT_CORE73", "CONFIG_WDT_CORE"),
            ("TCONFIG_CLKRST_CORE73", "CONFIG_CLKRST_CORE"),
            ("TCONFIG_IP_CORE73", "CONFIG_IP_CORE"),
            #("TCONFIG_HSE_CORE73", "CONFIG_HSE_CORE"),
            ("TCONFIG_MULTIBOOT_CORE73", "CONFIG_MULTIBOOT_CORE"),
            ("TCONFIG_LMMI_CORE73", "CONFIG_LMMI_CORE"),
        ]
    ),
    (FuzzConfig(job="CONFIGIP", device="LIFCL-17", sv="../shared/empty_17.v",
        tiles=["CIB_R0C66:EFB_15K", "CIB_R0C72:I2C_15K", "CIB_R0C71:OSC_15K", "CIB_R0C70:PMU_15K"]),
        [
            ("TCONFIG_WDT_CORE52", "CONFIG_WDT_CORE"),
            ("TCONFIG_CLKRST_CORE52", "CONFIG_CLKRST_CORE"),
            ("TCONFIG_IP_CORE52", "CONFIG_IP_CORE"),
            ("TCONFIG_CRE_CORE52", "CONFIG_CRE_CORE"),
            ("TCONFIG_MULTIBOOT_CORE52", "CONFIG_MULTIBOOT_CORE"),
            ("TCONFIG_LMMI_CORE52", "CONFIG_LMMI_CORE"),
        ]
    ),
]

def main():
    for cfg, sites in cfgs:
        cfg.setup()
        empty = cfg.build_design(cfg.sv, {})
        cfg.sv = "ip.v"
        def per_site(s):
            site, prim = s
            def get_substs(mode="NONE", default_cfg=False, kv=None, mux=False, extra_sigs=""):
                if kv is None:
                    config = ""
                elif mux:
                    val = "#SIG"
                    if kv[1] in ("0", "1"):
                        val = kv[1]
                    if kv[1] == "INV":
                        val = "#INV"
                    config = "{}::::{}={}{}".format(mode, kv[0], val, extra_sigs)
                else:
                    config = "{}:::{}={}".format(mode, kv[0], kv[1])
                return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, prim=prim, site=site)
            nonrouting.fuzz_enum_setting(cfg, empty, "{}.MODE".format(prim), ["NONE", prim],
                lambda x: get_substs(mode=x), False,
                desc="{} primitive mode".format(prim))
            for name, values, desc in settings[prim]:
                nonrouting.fuzz_enum_setting(cfg, empty, "{}.{}".format(prim, name), values,
                    lambda x,name=name,prim=prim: get_substs(mode=prim, kv=(name, x)), False,
                    desc=desc)
            if prim in words:
                for name, width, desc in words[prim]:
                    nonrouting.fuzz_word_setting(cfg, "{}.{}".format(prim, name), width,
                        lambda x,name=name,prim=prim: get_substs(mode=prim, kv=(name, "0b" + "".join(reversed(["1" if b else "0" for b in x])))),
                        desc=desc)
        fuzzloops.parallel_foreach(sites, per_site)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

