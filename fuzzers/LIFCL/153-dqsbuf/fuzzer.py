from fuzzconfig import FuzzConfig
import nonrouting
import fuzzloops
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

def per_loc(x):
    cfg = x["cfg"]

    cfg.setup()
    empty = cfg.build_design(cfg.sv, {})
    cfg.sv = "dqsbuf.v"

    r, c = x["rc"]
    site = "DQSBUF_CORE_R{}C{}".format(r, c)

    def get_substs(mode="DQSBUF_CORE", kv=None, mux=False):
        if kv is None:
            config = ""
        elif mux:
            val = "#SIG"
            if kv[1] in ("0", "1"):
                val = kv[1]
            if kv[1] == "INV":
                val = "#INV"
            config = "{}::::{}={}".format(mode, kv[0], val)
        else:
            config = "{}:::{}={}".format(mode, kv[0], kv[1])
        return dict(mode=mode, cmt="//" if mode == "NONE" else "", config=config, site=site)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.MODE", ["NONE", "DQSBUF_CORE"],
        lambda x: get_substs(mode=x), False,
        desc="DQSBUF primitive mode")
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.GSR", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("GSR", x)), False,
        desc="DQSBUF GSR mask")

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.ENABLE_FIFO", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("ENABLE_FIFO", x)), False,
        desc="DQSBUF read FIFO enable")
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.FORCE_READ", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("FORCE_READ", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.FREE_WHEEL", ["DDR", "GDDR"],
        lambda x: get_substs(kv=("FREE_WHEEL", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.MODX", ["NOT_USED", "MDDRX2", "MDDRX4"],
        lambda x: get_substs(kv=("MODX", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.MT_EN_READ", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("MT_EN_READ", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.MT_EN_WRITE", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("MT_EN_WRITE", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.MT_EN_WRITE_LEVELING", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("MT_EN_WRITE_LEVELING", x)), False)

    nonrouting.fuzz_word_setting(cfg, "DQSBUF.RD_PNTR", 3,
        lambda x: get_substs(kv=("RD_PNTR", "0b" + "".join(reversed(["1" if b else "0" for b in x])))))

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.READ_ENABLE", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("READ_ENABLE", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.RX_CENTERED", ["ENABLED", "DISABLED"],
        lambda x: get_substs(kv=("RX_CENTERED", x)), False)

    def intval(vec):
        x = 0
        for i, b in enumerate(vec):
            if b:
                x |= (1 << i)
        return x

    nonrouting.fuzz_word_setting(cfg, "DQSBUF.S_READ", 9,
        lambda x: get_substs(kv=("S_READ", str(intval(x)))))
    nonrouting.fuzz_word_setting(cfg, "DQSBUF.S_WRITE", 9,
        lambda x: get_substs(kv=("S_WRITE", str(intval(x)))))

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.SIGN_READ", ["POSITIVE", "COMPLEMENT"],
        lambda x: get_substs(kv=("SIGN_READ", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.SIGN_WRITE", ["POSITIVE", "COMPLEMENT"],
        lambda x: get_substs(kv=("SIGN_WRITE", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.UPDATE_QU", ["UP1_AND_UP0_SAME", "UP1_AHEAD_OF_UP0"],
        lambda x: get_substs(kv=("UPDATE_QU", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.SEL_READ_BIT_ENABLE_CYCLES", ["NORMAL", "DELAYED_0P5_ECLK"],
        lambda x: get_substs(kv=("SEL_READ_BIT_ENABLE_CYCLES", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.BYPASS_WR_LEVEL_SMTH_LATCH", ["SMOOTHING_PATH", "BYPASS_PATH"],
        lambda x: get_substs(kv=("BYPASS_WR_LEVEL_SMTH_LATCH", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.BYPASS_WR_SMTH_LATCH", ["SMOOTHING_PATH", "BYPASS_PATH"],
        lambda x: get_substs(kv=("BYPASS_WR_SMTH_LATCH", x)), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.BYPASS_READ_SMTH_LATCH", ["SMOOTHING_PATH", "BYPASS_PATH"],
        lambda x: get_substs(kv=("BYPASS_READ_SMTH_LATCH", x)), False)

    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.PAUSEMUX", ["0", "PAUSE"],
        lambda x: get_substs(kv=("PAUSE", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.RSTMUX", ["RST", "INV"],
        lambda x: get_substs(kv=("RST", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.SCLKMUX", ["SCLK", "INV"],
        lambda x: get_substs(kv=("SCLK", x), mux=True), False)
    nonrouting.fuzz_enum_setting(cfg, empty, "DQSBUF.RSTSMCNTMUX", ["RSTSMCNT", "INV"],
        lambda x: get_substs(kv=("RSTSMCNT", x), mux=True), False)
def main():
    fuzzloops.parallel_foreach(configs, per_loc)
if __name__ == "__main__":
    fuzzloops.FuzzerMain(main)

