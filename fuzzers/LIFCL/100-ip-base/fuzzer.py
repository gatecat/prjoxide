import fuzzconfig
import nonrouting
import fuzzloops
import database
from os import path
import libpyprjoxide
import json

cfg = fuzzconfig.FuzzConfig(job="IPADDR", device="LIFCL-40", sv="ip.v", tiles=[])

# Config to make sure we get at least one IP bit set
ip_settings = {
    "EBR_CORE_WID0": "EBR_CORE:::WID=0b00000000000",
    "EBR_CORE_WID1": "EBR_CORE:::WID=0b00000000001",
    "EBR_CORE_WID2047": "EBR_CORE:::WID=0b11111111111",
    "DPHY_CORE": "DPHY_CORE:::U_PRG_HS_TRAIL=0b000001",
    "PLL_CORE": "PLL_CORE:::DIVA=1",
    "PMU_CORE": "PMU_CORE:::WKCOUNT0=0b00000001",
    "SGMIICDR_CORE": "SGMIICDR_CORE:::DCOITUNE4LSB=15_PERCENT",
    "I2CFIFO_CORE": "I2CFIFO_CORE:::I2CSLVADDRA=0b0000000001",
    "PCIE_CORE": "PCIE_CORE:::PHY_MODE=0b0001",
    "LRAM_CORE": "LRAM_CORE:::CFG_INIT_ID=0b00000000000",
}

ip_abits = {
    "DPHY_CORE": 5,
    "PLL_CORE": 7,
    "PMU_CORE": 4,
    "SGMIICDR_CORE": 4,
    "I2CFIFO_CORE": 6,
    "PCIE_CORE": 17,
    "EBR_CORE": 17,
    "LRAM_CORE": 17,
}

ip_sites = [
    ("TDPHY_CORE2", "DPHY_CORE"),
    ("TDPHY_CORE26", "DPHY_CORE"),
    ("PLL_LLC", "PLL_CORE"),
    ("PLL_LRC", "PLL_CORE"),
    ("PLL_ULC", "PLL_CORE"),
    ("PMU_CORE_R1C85", "PMU_CORE"),
    ("LSGMIICDR_CORE51", "SGMIICDR_CORE"),
    ("LSGMIICDR_CORE52", "SGMIICDR_CORE"),
    ("I2CFIFO_CORE_R1C81", "I2CFIFO_CORE"),
    ("TPCIE_CORE57", "PCIE_CORE"),
    ("EBR_CORE_R28C26", "EBR_CORE_WID0"),
    ("EBR_CORE_R28C26", "EBR_CORE_WID1"),
    ("EBR_CORE_R28C26", "EBR_CORE_WID2047"),
    ("LRAM_CORE_R18C86", "LRAM_CORE"),
    ("LRAM_CORE_R40C86", "LRAM_CORE"),
]

def main():
    cfg.setup(skip_specimen=True)
    ip_base = {}
    for site, prim in ip_sites:
        prim_type = prim
        wid_idx = prim_type.find("_WID")
        if wid_idx != -1:
            prim_type = prim_type[0:wid_idx]
        bit = cfg.build_design(cfg.sv, dict(cmt="", prim=prim_type, site=site, config=ip_settings[prim]))
        chip = libpyprjoxide.Chip.from_bitstream(fuzzconfig.db, bit)
        ipv = chip.get_ip_values()
        assert len(ipv) > 0
        addr = ipv[0][0]
        ip_name = site
        if "EBR_CORE" in ip_name:
            ip_name = prim.replace("_CORE", "")
        #if "LRAM_CORE" in ip_name:
        #    ip_name = "LRAM"
        ip_base[ip_name] = {
            "addr": addr & ~((1 << ip_abits[prim_type]) - 1),
            "abits": ip_abits[prim_type]
        }
    with open(path.join(database.get_db_root(), "LIFCL", "LIFCL-40", "baseaddr.json"), "w") as jf:
        print(json.dumps(dict(regions=ip_base), sort_keys=True, indent=4), file=jf)
    
if __name__ == "__main__":
    main()
