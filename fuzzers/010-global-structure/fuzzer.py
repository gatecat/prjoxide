import logging
import os

import database
import lapie
import json
from fuzzconfig import FuzzConfig, should_fuzz_platform
from tiles import pos_from_name
from os import path
import database
from collections import defaultdict
import tiles

import fuzzloops
# name max_row max_col
import fuzzconfig

def main():
    families = database.get_devices()["families"]
    devices = sorted([
        device
        for family in families
        for device in families[family]["devices"]
        if fuzzconfig.should_fuzz_platform(device)
    ])

    for name in devices:
        if not should_fuzz_platform(name):
            continue
        logging.info(f"Finding globals for {name}")
        cfg = FuzzConfig(job="GLOBAL_{}".format(name), device=name, sv="../shared/empty.v", tiles=[])
        cfg.setup()
        db_path = path.join(database.get_db_root(), database.get_family_for_device(name), name, "globals.json")
        def load_db():
            if path.exists(db_path):
                with open(db_path, "r") as dbf:
                   return json.load(dbf)
            else:
                return {"branches": []}
        def save_db():
            # Clear the sym link if this isn't the main db
            os.remove(db_path)
            with open(db_path, "w") as dbf:
                print(json.dumps(gdb, sort_keys=True, indent=4), file=dbf)
        gdb = load_db()

        devices = database.get_devices()
        family = database.get_family_for_device(name)
        device_info = devices["families"][family]["devices"][name]
        max_row = device_info["max_row"]
        max_col = device_info["max_col"]

        tg = database.get_tilegrid(cfg.device)["tiles"]
        tap_plcs = set([v['x'] for k, v in tg.items() if v["tiletype"].startswith("TAP_PLC")])

        # Determine branch driver locations
        test_row = 4
        clock_wires = ["R{}C{}_JCLK0".format(test_row, c) for c in range(1, max_col)]
        clock_info = lapie.get_node_data(cfg.device, clock_wires)
        branch_to_col = defaultdict(list)
        for n in clock_info:
            r, c = pos_from_name(n.name)
            hpbx_c = None
            for uh in n.uphill_pips:
                if "_HPBX0" in uh.from_wire:
                    hpbx_r, hpbx_c = pos_from_name(uh.from_wire)
                    assert hpbx_r == r
                    break
            assert hpbx_c is not None
            branch_to_col[hpbx_c].append(c)
        branches = []

        # Trace back the nodes which connect the tap to the spine
        branch_wires = [f"R{test_row}C{bc}_HPBX0000" for bc in sorted(branch_to_col.keys())]
        if name == "LIFCL-17":
            branch_wires.append("R{}C13_RHPBX0000".format(test_row))
        branch_wire_info = lapie.get_node_data(cfg.device, branch_wires)
        if len(branch_wire_info) == 0:
            logging.warning(f"No nodes found for {branch_wires} {test_row}")
        branch_driver_col = {}
        # Branches directly driven by a VPSX
        # Also, get a test column for the spine exploration later

        for bw in branch_wire_info:
            r, c = pos_from_name(bw.name)
            for uh in bw.uphill_pips:
                if "VPSX" in uh.from_wire:
                    vpsx_r, vpsx_c = pos_from_name(uh.from_wire)
                    branch_driver_col[c] = vpsx_c

        sp_test_col = sorted(branch_driver_col.keys())[len(sorted(branch_driver_col.keys()))//2]

        # Branches driven by another branch
        for bw in branch_wire_info:
            r, c = pos_from_name(bw.name)
            if c in branch_driver_col:
                continue
            for uh in bw.uphill_pips:
                if "HPBX0" in uh.from_wire:
                    hpbx_r, hpbx_c = pos_from_name(uh.from_wire)
                    branch_driver_col[c] = branch_driver_col[hpbx_c]
        for bc, scs in sorted(branch_to_col.items()):
            tap_drv_distances = [(abs(x - branch_driver_col[bc]), x) for x in tap_plcs]
            tap_drv_col = min(tap_drv_distances)[1]
            side = "R" if branch_driver_col[bc] < bc else "L"
            if tap_drv_col in tap_plcs:
                logging.info(f"Tap drv col {tap_drv_col} {bc} {sorted(scs)}")
            branches.append(dict(branch_col=bc, tap_driver_col=tap_drv_col, tap_side=side, from_col=min(scs), to_col=max(scs)))
        gdb["branches"] = branches
        save_db()
        # Spines
        sp_branch_wires = ["R{}C{}_HPBX0000".format(r, sp_test_col) for r in range(1, max_row)]
        spine_to_branch_row = {}
        sp_info = lapie.get_node_data(cfg.device, sp_branch_wires)
        if len(sp_info) == 0:
            logging.warning(f"No nodes found for {sp_branch_wires} {sp_test_col}")
        for n in sp_info:
            r, c = pos_from_name(n.name)
            vpsx_r = None
            for uh in n.uphill_pips:
                if "VPSX" in uh.from_wire:
                    vpsx_r, vpsx_c = pos_from_name(uh.from_wire)
                    break
            assert vpsx_r is not None
            if vpsx_r not in spine_to_branch_row:
                spine_to_branch_row[vpsx_r] = []
            spine_to_branch_row[vpsx_r].append(r)
        spines = []

        sp_test_row = None
        logging.info(f"spine_to_branch_row {spine_to_branch_row}")
        for sr, brs in sorted(spine_to_branch_row.items()):
            if sp_test_row is None:
                sp_test_row = sr
            spines.append(dict(spine_row=sr, from_row=min(brs), to_row=max(brs)))
        gdb["spines"] = spines
        save_db()
        # HROWs
        hrow_to_spine_rcs = {}
        spine_wires = ["R{}C{}_VPSX0000".format(sp_test_row, c) for c in sorted(set(branch_driver_col.values()))]
        hr_info = lapie.get_node_data(cfg.device, spine_wires)
        for n in hr_info:
            r, c = pos_from_name(n.name)
            hrow_c = None
            for uh in n.uphill_pips:
                if "HPRX0" in uh.from_wire:
                    hrow_r, hrow_c = pos_from_name(uh.from_wire)
                    break
            assert hrow_c is not None
            if hrow_r is not None:
                if (hrow_r, hrow_c) not in hrow_to_spine_rcs:
                    hrow_to_spine_rcs[(hrow_r, hrow_c)] = []
                hrow_to_spine_rcs[(hrow_r, hrow_c)].append((r,c))
        hrows = []
        sp_test_row = None
        for hrc, scs in sorted(hrow_to_spine_rcs.items()):
            hrows.append(dict(hrow_col=hrc[1], hrow_row=hrc[0], spine_cols=sorted([x[1] for x in scs])))
        gdb["hrows"] = hrows
        logging.info(gdb)
        save_db()
        
if __name__ == '__main__':
    fuzzloops.FuzzerMain(main)

