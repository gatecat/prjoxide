import json
from collections import defaultdict
from pathlib import Path

from cffi.model import PrimitiveType
import logging

class PrimitiveSetting:
    def __init__(self, name, desc, depth=3, enable_value=None):
        self.name = name
        self.desc = desc
        self.depth = depth

        # The enable value for a setting is the one that is required or sufficient to turn the primitive on in the bit
        # stream. None means the values of this setting have no enable effect on the primitive mode.
        self.enable_value = enable_value

    def format(self, prim, value):
        if self.depth == -1:
            return f"{self.name}:{value}"

        k = self.name
        seperator = ":" * self.depth
        if "." not in k:
            k = prim.primitive + seperator + k
        else:
            k = k.replace(".", seperator)
        return f"{k}={value}"


class PinSetting(PrimitiveSetting):
    def __init__(self, name, dir, desc="", bits=None):
        super().__init__(name, desc)
        self.dir = dir
        self.bits = bits

    def __repr__(self):
        return f'PinSetting(name = "{self.name}", dir = "{self.dir}", desc = "{self.desc}", bits = {self.bits})'


class WordSetting(PrimitiveSetting):
    def __init__(self, name, bits, default=None, desc="", number_formatter=None, enable_value=None):
        super().__init__(name, desc, enable_value=enable_value)
        self.bits = bits
        self.default = default
        self.number_formatter = number_formatter
        if self.number_formatter is None:
            self.number_formatter = lambda _, x: x

    def binary_formatter(self, v):
        return f"0b{v:0{self.bits}b}"

    def signed_formatter(self, v):
        return (-1 if (1 << self.bits) else 1) * (~(1 << self.bits) & v)

    def format(self, prim, value):
        return super().format(prim, self.number_formatter(self, value))

    def fill_value(self):
        return 1

class EnumSetting(PrimitiveSetting):
    def __init__(self, name, values, default=None, desc="", enable_value=None, depth=3):
        super().__init__(name, desc, enable_value=enable_value)
        self.values = values
        self.default = default

    def fill_value(self):
        return self.values[-1]

class ProgrammablePin(EnumSetting):
    def __init__(self, name, values, desc="", primitive = None):
        super().__init__(name, values, desc=desc, depth=4)
        if primitive is None:
            primitive = name + "MUX"
        self.primitive = primitive

    def format(self, prim, value):
        if value == "#OFF":
            return f"{self.primitive}:#OFF"
        elif value[0] == "#":
            #return f"{self.primitive}:{self.name}:::{self.name}={value}"
            return f"{self.primitive}::::{self.name}={value}"
        else:
            return f"{self.primitive}:CONST:::CONST={value}"
        raise Exception(f"Unknown value {value}")


primitives = defaultdict(list)


class PrimitiveDefinition(object):
    def __init__(self, site_type, settings=[], pins=[], mode=None, desc=None, primitive=None, beltype=None, belname=None):
        self.site_type = site_type
        self.mode = mode
        self.desc = desc
        self.primitive = primitive
        self.beltype = beltype
        self.needs_overlay = False
        if self.mode is None:
            self.mode = self.site_type
        if self.primitive is None:
            self.primitive = self.mode

        primitives[self.site_type].append(self)

        self.settings = settings
        self.pins = pins
        self._belname = belname

    def belname(self, site, site_info, ts):
        if isinstance(self._belname, str):
            return self._belname
        if callable(self._belname):
            return self._belname(site, site_info, ts)
        return site

    def get_setting(self, name):
        settings = {s.name: s for s in self.settings}
        return settings[name]

    def configuration(self, values):
        enable_values = {s.name: s.enable_value for s in self.settings if s.enable_value is not None}
        settings = {s.name: s for s in self.settings}
        if isinstance(values, dict):
            values = list(values.items())

        def find_setting(x):
            k, v = x
            if isinstance(k, str):
                return (settings.get(k), v)
            return x

        values = list(map(find_setting, values))
        for k, v in values:
            enable_values.pop(k.name, None)

        for x in enable_values.items():
            values.append(find_setting(x))

        return f"MODE:{self.mode} " + " ".join([s.format(self, v) for (s, v) in values])

    def default_config(self):
        return self.configuration({s: s.enable_value for s in self.settings if s.enable_value is not None})

    def fill_config(self):
        return self.configuration({s: s.fill_value() for s in self.settings})

    @staticmethod
    def parse_primitive_json(primitive, site_type=None, core_suffix=True, mode = None, value_sizes={}, beltype=None):
        import database

        parsed = database.get_primitive_json(primitive)

        if core_suffix and site_type is None:
            primitive = primitive + "_CORE"

        if mode is None:
            mode = primitive

        def create_setting(s):
            values = s.get("Value", s.get("Values"))
            name = s.get("Name", s.get("Attribute"))

            if values is None:
                logging.warning(f"No values for {primitive}")
                return None

            if len(values) == 1:
                word_size = None
                number_formatter = None
                try:
                    if values[0].startswith("0b"):
                        word_size = len(values[0].split("0b")[-1])
                        default_value = 0
                        number_formatter = WordSetting.binary_formatter
                    else:
                        default_value = int(values[0])
                except:
                    default_value = 0
                    logging.error(f"Could not parse {values[0]} for {name} into default value")

                if word_size is None:
                    word_size = value_sizes.get(name)
                if word_size is None:
                    word_size = value_sizes.get("")
                if word_size is None:
                    logging.warning(f"Need size annotation for {name}")
                    return None

                return WordSetting(name, word_size, desc=name, default=default_value, number_formatter=number_formatter)

            if values[0].replace("`", "").startswith("0b"):
                bit_cnt = len(values[0].replace("`", "").split(" ")[0].split("0b")[-1])
                return WordSetting(name, bit_cnt, desc=name, number_formatter=WordSetting.binary_formatter)

            return EnumSetting(name, values, desc=str(s.get("Description", "")), default=values[0])

        parameters_key = "Parameters"
        if parameters_key not in parsed:
            parameters_key = [k for k in parsed.keys() if "parameters" in k.lower()][0]

        def create_pin(pin_def, dir):
            range = pin_def.get("Range", "")
            name = pin_def["Name"]
            if '[' in name:
                range = name.split("[")[1].replace("]", "")
                name = name.split("[")[0]
            desc = pin_def["Description"]

            if ":" in range:
                range = range.split(":")
                assert range[1] == "0"
                range = int(range[0])
            else:
                range = None

            return PinSetting(name, dir, desc, bits=range)

        pins = [create_pin(p, dir) for (name, dir) in {"Output Ports": "out", "Input Ports": "in"}.items() for p in
                parsed[name]]

        return PrimitiveDefinition(
            site_type=site_type if site_type else mode,
            settings=[create_setting(s) for s in parsed[parameters_key]],
            pins=pins,
            desc=parsed.get("description", ""),
            mode=mode,
            primitive=primitive,
            beltype=beltype
        )

def lram_core_belname(site, site_info, ts):
    tt = ts[0].split(":")[-1]
    return f"LRAM{tt.split('_')[1]}"

lram_core = PrimitiveDefinition(
    "LRAM_CORE",
    beltype = "LRAM_CORE",
    belname=lram_core_belname,
    settings =
    [
        EnumSetting("ASYNC_RST_RELEASE", ["SYNC", "ASYNC"],
                    desc="LRAM reset release configuration"),
        EnumSetting("DATA_PRESERVE", ["DISABLE", "ENABLE"],
                    desc="LRAM data preservation across resets"),
        EnumSetting("EBR_SP_EN", ["DISABLE", "ENABLE"],
                    desc="EBR single port mode"),
        EnumSetting("ECC_BYTE_SEL", ["ECC_EN", "BYTE_EN"]),
        EnumSetting("GSR", ["ENABLED", "DISABLED"],
                    desc="LRAM global set/reset mask"),
        EnumSetting("OUT_REGMODE_A", ["NO_REG", "OUT_REG"],
                    desc="LRAM output pipeline register A enable"),
        EnumSetting("OUT_REGMODE_B", ["NO_REG", "OUT_REG"],
                    desc="LRAM output pipeline register B enable"),
        EnumSetting("RESETMODE", ["SYNC", "ASYNC"],
                    desc="LRAM sync/async reset select"),
        EnumSetting("RST_AB_EN", ["RESET_AB_DISABLE", "RESET_AB_ENABLE"],
                    desc="LRAM reset A/B enable"),
        EnumSetting("SP_EN", ["DISABLE", "ENABLE"],
                    desc="LRAM single port mode"),
        EnumSetting("UNALIGNED_READ", ["DISABLE", "ENABLE"],
                    desc="LRAM unaligned read support"),
        ProgrammablePin("CLK", ["#SIG", "#INV"], desc="LRAM CLK inversion control", primitive="LRAM_CORE"),
        ProgrammablePin("CSA", ["#SIG", "#INV"], desc="LRAM CSA inversion control", primitive="LRAM_CORE"),
        ProgrammablePin("CSB", ["#SIG", "#INV"], desc="LRAM CSB inversion control", primitive="LRAM_CORE"),
        ProgrammablePin("RSTA", ["#SIG", "#INV"], desc="LRAM RSTA inversion control", primitive="LRAM_CORE"),
        ProgrammablePin("RSTB", ["#SIG", "#INV"], desc="LRAM RSTB inversion control", primitive="LRAM_CORE"),
        ProgrammablePin("WEA", ["#SIG", "#INV"], desc="LRAM WEA inversion control", primitive="LRAM_CORE"),
        #ProgrammablePin("WEB", ["#SIG", "#INV"], desc="LRAM WEB inversion control", primitive="LRAM_CORE"),
    ]
)

iologic_core = PrimitiveDefinition(
    "IOLOGIC_CORE",
    [
        WordSetting("DELAYA.DEL_VALUE", 7, enable_value=1),
        EnumSetting("DELAYA.COARSE_DELAY", ["0NS", "0P8NS", "1P6NS"]),
        EnumSetting("DELAYA.COARSE_DELAY_MODE", ["DYNAMIC", "STATIC"]),
        EnumSetting("DELAYA.EDGE_MONITOR", ["ENABLED", "DISABLED"]),
        EnumSetting("DELAYA.WAIT_FOR_EDGE", ["ENABLED", "DISABLED"]),
    ]+ [ProgrammablePin(n, ["#SIG", "#OFF"])
         for n in
         ["CIBCRS0", "CIBCRS1", "RANKSELECT", "RANKENABLE", "RANK0UPDATE", "RANK1UPDATE"]
         ],
    mode="IREG_OREG"
)

delayb = PrimitiveDefinition.parse_primitive_json("DELAYB",
                                                  site_type="SIOLOGIC_CORE", mode="IREG_OREG", value_sizes={"DEL_VALUE": 7})
# siologic_core = PrimitiveDefinition(
#     "SIOLOGIC_CORE",
#     [
#         WordSetting("DELAYB.DEL_VALUE", 7, enable_value=1),
#         EnumSetting("DELAYB.COARSE_DELAY", ["0NS", "0P8NS", "1P6NS"]),
#         EnumSetting("DELAYB.COARSE_DELAY_MODE", ["DYNAMIC", "STATIC"]),
#         EnumSetting("DELAYB.EDGE_MONITOR", ["ENABLED", "DISABLED"]),
#         EnumSetting("DELAYB.WAIT_FOR_EDGE", ["ENABLED", "DISABLED"]),
#     ] ,
#     mode="IREG_OREG"
# )

delayb.get_setting("DEL_VALUE").enable_value = 1
delayb.get_setting("GSR").depth = -1
delayb.pins = []

osc_core = PrimitiveDefinition(
    "OSC_CORE",
    [
        WordSetting("HF_CLK_DIV", 8,
                    desc="high frequency oscillator output divider"),
        WordSetting("HF_SED_SEC_DIV", 8,
                    desc="high frequency oscillator output divider"),
        EnumSetting("DTR_EN", ["ENABLED", "DISABLED"]),
        EnumSetting("HF_FABRIC_EN", ["ENABLED", "DISABLED"],
                    desc="enable HF oscillator trimming from input pins"),
        EnumSetting("HF_OSC_EN", ["ENABLED", "DISABLED"],
                    desc="enable HF oscillator"),
        EnumSetting("HFDIV_FABRIC_EN", ["ENABLED", "DISABLED"],
                    desc="enable HF divider from parameter"),
        EnumSetting("LF_FABRIC_EN", ["ENABLED", "DISABLED"],
                    desc="enable LF oscillator trimming from input pins"),
        EnumSetting("LF_OUTPUT_EN", ["ENABLED", "DISABLED"],
                    desc="enable LF oscillator output"),
        EnumSetting("DEBUG_N", ["ENABLED", "DISABLED"],
                    desc="enable debug mode"),
    ],
    [
        PinSetting("HFCLKOUT", "out"),
        PinSetting("HFSDSCEN", "in")
    ],
)

oscd_core = PrimitiveDefinition(
    "OSCD_CORE",
    beltype="OSCD",
    belname="OSCD",
    settings=[
        EnumSetting("DTR_EN", ["ENABLED", "DISABLED"]),

        WordSetting("HF_CLK_DIV", 8, default=1),

        WordSetting("HF_SED_SEC_DIV", 8),

        EnumSetting("HF_FABRIC_EN", ["ENABLED", "DISABLED"]),

        EnumSetting("HF_OSC_EN", ["ENABLED", "DISABLED"],
                    default="ENABLED", enable_value="ENABLED"),

        EnumSetting("LF_FABRIC_EN", ["ENABLED", "DISABLED"]),

        EnumSetting("LF_OUTPUT_EN", ["ENABLED", "DISABLED"]),

        EnumSetting("DEBUG_N", ["ENABLED", "DISABLED"]),
    ],
    pins=[
        PinSetting("HFOUTEN", dir="in"),
        PinSetting("HFSDSCEN", dir="in"),
        PinSetting("HFOUTCIBEN", dir="in"),
        PinSetting("REBOOT", dir="in"),
        PinSetting("HFCLKOUT", dir="out"),
        PinSetting("LFCLKOUT", dir="out"),
        PinSetting("HFCLKCFG", dir="out"),
        PinSetting("HFSDCOUT", dir="out"),
    ],
)

dcc = PrimitiveDefinition.parse_primitive_json("DCC", core_suffix=False)
dcc.beltype = "DCC"
dcc.get_setting("DCCEN").enable_value = "1"
dcc.settings[0].desc = "DCC bypassed (0) or used as gate (1)"

PrimitiveDefinition(
    "DCS",
    beltype="DCS",
    settings=[
        EnumSetting("DCSMODE",
                    ["VCC", "GND", "DCS", "DCS_1", "BUFGCECLK0", "BUFGCECLK0_1", "BUFGCECLK1", "BUFGCECLK1_1", "BUF0",
                     "BUF1"], desc="clock selector mode", enable_value="DCS"),
    ]
)

pll_value_sizes = {"": 9, "DYN_SEL": 3, "EXTERNAL_DIVIDE_FACTOR": 6}
for k in ["A", "B", "C", "D", "E", "F"]:
    pll_value_sizes[f"DEL{k}"] = 7
    pll_value_sizes[f"DIV{k}"] = 7
    pll_value_sizes[f"PHI{k}"] = 3

pll_core = PrimitiveDefinition.parse_primitive_json("PLL", core_suffix=True, value_sizes=pll_value_sizes, beltype="PLL_CORE")
for s in pll_core.settings:
    if s.name.startswith("ENCLK_"):
        s.enable_value = "ENABLED"
pll_core.settings = [s for s in pll_core.settings if s.name != "CONFIG_WAIT_FOR_LOCK"]
pll_core.pins = [
    PinSetting(name="INTFBK0", dir="out", bits=None),
    PinSetting(name="INTFBK1", dir="out", bits=None),
    PinSetting(name="INTFBK2", dir="out", bits=None),
    PinSetting(name="INTFBK3", dir="out", bits=None),
    PinSetting(name="INTFBK4", dir="out", bits=None),
    PinSetting(name="INTFBK5", dir="out", bits=None),
    PinSetting(name="LMMIRDATA", dir="out", bits=7),
    PinSetting(name="LMMIRDATAVALID", dir="out", bits=None),
    PinSetting(name="LMMIREADY", dir="out", bits=None),
    PinSetting(name="CLKOP", dir="out", bits=None),
    PinSetting(name="CLKOS", dir="out", bits=None),
    PinSetting(name="CLKOS2", dir="out", bits=None),
    PinSetting(name="CLKOS3", dir="out", bits=None),
    PinSetting(name="CLKOS4", dir="out", bits=None),
    PinSetting(name="CLKOS5", dir="out", bits=None),
    PinSetting(name="INTLOCK", dir="out", bits=None),
    PinSetting(name="LEGRDYN", dir="out", bits=None),
    PinSetting(name="LOCK", dir="out", bits=None),
    PinSetting(name="PFDDN", dir="out", bits=None),
    PinSetting(name="PFDUP", dir="out", bits=None),
    PinSetting(name="REFMUXCK", dir="out", bits=None),
    PinSetting(name="REGQA", dir="out", bits=None),
    PinSetting(name="REGQB1", dir="out", bits=None),
    PinSetting(name="CLKOUTDL", dir="out", bits=None),

    #PinSetting(name="LOADREG", dir="in",bits=None),
    #PinSetting(name="DYNROTATE", dir="in", bits=None),
    PinSetting(name="LMMICLK", dir="in", bits=None),
    PinSetting(name="LMMIRESETN", dir="in",
               bits=None),
    PinSetting(name="LMMIREQUEST", dir="in", bits=None),
    PinSetting(name="LMMIWRRDN", dir="in", bits=None),
    PinSetting(name="LMMIOFFSET", dir="in",
               bits=6),
    PinSetting(name="LMMIWDATA", dir="in",
               bits=7),

    PinSetting(name="REFCK", dir="in", bits=None),
    PinSetting(name="ENCLKOP", dir="in", bits=None),
    PinSetting(name="ENCLKOS", dir="in", bits=None),
    PinSetting(name="ENCLKOS2", dir="in", bits=None),
    PinSetting(name="ENCLKOS3", dir="in", bits=None),
    PinSetting(name="ENCLKOS4", dir="in", bits=None),
    PinSetting(name="ENCLKOS5", dir="in", bits=None),
    PinSetting(name="FBKCK", dir="in", bits=None),
    PinSetting(name="LEGACY", dir="in", bits=None),
    PinSetting(name="PLLRESET", dir="in",
               bits=None),
    PinSetting(name="STDBY", dir="in",
               bits=None),
    PinSetting(name="ROTDEL", dir="in", bits=None),
    PinSetting(name="DIRDEL", dir="in", bits=None),
    PinSetting(name="ROTDELP1", dir="in", bits=None),

    PinSetting(name="BINTEST", dir="in", bits=1),
    PinSetting(name="DIRDELP1", dir="in", bits=None),
    PinSetting(name="GRAYACT", dir="in", bits=4),
    PinSetting(name="BINACT", dir="in", bits=1)
]

# The documentation has this but its for DIFFIO
def remove_failsafe_enum(definition):
    for setting in definition.settings:
        if hasattr(setting, "values") and "FAILSAFE" in setting.values:
            setting.values.remove("FAILSAFE")
    return definition

# These work but are specially handled right now
#seio33 = remove_failsafe_enum(PrimitiveDefinition.parse_primitive_json("SEIO33"))
#seio18 = remove_failsafe_enum(PrimitiveDefinition.parse_primitive_json("SEIO18"))
#PrimitiveDefinition.parse_primitive_json("DIFFIO18")

eclkdiv = PrimitiveDefinition.parse_primitive_json("ECLKDIV")
eclkdiv.get_setting("ECLK_DIV").enable_value = "2"

# This definition is from 2024 web docs
pclkdiv = PrimitiveDefinition(
    "PCLKDIV",
    beltype="PCLKDIV",
    settings=[
        EnumSetting("DIV_PCLKDIV", [
        "X1",
        "X2",
        "X4",
        "X8",
        "X16",
        "X32",
        "X64",
        "X128"
      ], desc="Divisor applied to clkin"),
    ],
)
pclkdiv.needs_overlay = True

def dlldel_belname(site, site_info, ts):
    tt = ts[0].split(":")[-1]
    return f"DLLDEL{tt.split('_')[-1]}"

dlldel = PrimitiveDefinition.parse_primitive_json("DLLDEL", value_sizes={"ADJUST": 9})
dlldel.beltype = "DLLDEL"
dlldel.needs_overlay = True
dlldel.belname = dlldel_belname
dlldel.get_setting("ENABLE").enable_value = "ENABLED"
dlldel.settings.append(
    ProgrammablePin("CLKIN", ["#SIG", "#INV"], desc="CLK inversion control", primitive="DLLDEL_CORE"),
)


wdt = PrimitiveDefinition(
    "CONFIG_WDT_CORE",
    mode="CONFIG_WDT_CORE",
    beltype="WDT",
    belname="WDT",
    settings=[
        EnumSetting("WDTEN", ["DIS", "EN"], enable_value="EN"),
        EnumSetting("WDTMODE", ["SINGLE", "CONTINUOUS"]),
        #WordSetting("WDTVALUE", 32) # Doesnt like it? might have weird formatting?
    ]
)
# Doesn't work right now -- seems optimimized out?
# i2cfifo = PrimitiveDefinition.parse_primitive_json("I2CFIFO")
# i2cfifo.get_setting("CR1GCEN").enable_value = "EN"
# i2cfifo.get_setting("CR1I2CEN").enable_value = "EN"
