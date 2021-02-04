import database
import lapie
import json
from fuzzconfig import FuzzConfig
from tiles import pos_from_name
from os import path

# name max_row max_col
configs = [
    ("LIFCL-40", 56, 87, "../shared/empty_40.v"),
    ("LIFCL-17", 29, 75, "../shared/empty_17.v"),
]

def main():
    for name, max_row, max_col, sv in configs:
        cfg = FuzzConfig(job="GLOBAL_{}".format(name), device=name, sv=sv, tiles=[])
        cfg.setup()
        db_path = path.join(database.get_db_root(), "LIFCL", name, "globals.json")
        def load_db():
            if path.exists(db_path):
                with open(db_path, "r") as dbf:
                   return json.load(dbf)
            else:
                return {"branches": []}
        def save_db():
            with open(db_path, "w") as dbf:
                print(json.dumps(gdb, sort_keys=True, indent=4), file=dbf)
        gdb = load_db()
        # Determine branch driver locations
        test_row = 4
        clock_wires = ["R{}C{}_JCLK0".format(test_row, c) for c in range(1, max_col)]
        clock_info = lapie.get_node_data(cfg.udb, clock_wires)
        branch_to_col = {}
        for n in clock_info:
            r, c = pos_from_name(n.name)
            hpbx_c = None
            for uh in n.uphill_pips:
                if "_HPBX0" in uh.from_wire:
                    hpbx_r, hpbx_c = pos_from_name(uh.from_wire)
                    assert hpbx_r == r
                    break
            assert hpbx_c is not None
            if hpbx_c not in branch_to_col:
                branch_to_col[hpbx_c] = []
            branch_to_col[hpbx_c].append(c)
        branches = []

        branch_wires = ["R{}C{}_HPBX0000".format(test_row, bc) for bc in sorted(branch_to_col.keys())]
        if name == "LIFCL-17":
            branch_wires.append("R{}C13_RHPBX0000".format(test_row))
        branch_wire_info = lapie.get_node_data(cfg.udb, branch_wires)
        branch_driver_col = {}
        # Branches directly driven by a VPSX
        # Also, get a test column for the spine exploration later
        sp_test_col = None
        for bw in branch_wire_info:
            r, c = pos_from_name(bw.name)
            for uh in bw.uphill_pips:
                if "VPSX" in uh.from_wire:
                    vpsx_r, vpsx_c = pos_from_name(uh.from_wire)
                    branch_driver_col[c] = vpsx_c
                    if sp_test_col is None:
                        sp_test_col = c
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
            tap_drv_col = branch_driver_col[bc] + 1
            side = "R" if tap_drv_col < bc else "L" 
            branches.append(dict(branch_col=bc, tap_driver_col=tap_drv_col, tap_side=side, from_col=min(scs), to_col=max(scs)))
        gdb["branches"] = branches
        save_db()
        # Spines
        sp_branch_wires = ["R{}C{}_HPBX0000".format(r, sp_test_col) for r in range(1, max_row)]
        spine_to_branch_row = {}
        sp_info = lapie.get_node_data(cfg.udb, sp_branch_wires)
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
        for sr, brs in sorted(spine_to_branch_row.items()):
            if sp_test_row is None:
                sp_test_row = sr
            spines.append(dict(spine_row=sr, from_row=min(brs), to_row=max(brs)))
        gdb["spines"] = spines
        save_db()
        # HROWs
        hrow_to_spine_col = {}
        spine_wires = ["R{}C{}_VPSX0000".format(sp_test_row, c) for c in sorted(set(branch_driver_col.values()))]
        hr_info = lapie.get_node_data(cfg.udb, spine_wires)
        for n in hr_info:
            r, c = pos_from_name(n.name)
            hrow_c = None
            for uh in n.uphill_pips:
                if "HPRX0" in uh.from_wire:
                    hrow_r, hrow_c = pos_from_name(uh.from_wire)
                    break
            assert hrow_c is not None
            if hrow_c not in hrow_to_spine_col:
                hrow_to_spine_col[hrow_c] = []
            hrow_to_spine_col[hrow_c].append(c)
        hrows = []
        sp_test_row = None
        for hrc, scs in sorted(hrow_to_spine_col.items()):
            hrows.append(dict(hrow_col=hrc, spine_cols=scs))
        gdb["hrows"] = hrows
        save_db()
if __name__ == '__main__':
    main()

