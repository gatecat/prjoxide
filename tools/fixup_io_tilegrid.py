import database
import tiles
import json
from os import path

"""
Despite Lattice assigning them the same tile type; "odd" and "even" top/left/right IO
locations have slightly different routing - swapped output tristate and data

This script fixes this by patching tile names
"""

for f, d in [("LIFCL", "LIFCL-40"), ("LIFCL", "LFD2NX-40"), ("LFCPNX", "LFCPNX-100")]:
    tgp = path.join(database.get_db_root(), f, d, "tilegrid.json")
    with open(tgp, "r") as infile:
        tg = json.load(infile)["tiles"]

    tiles_by_xy = [[]]
    max_row = 0
    max_col = 0
    for tile in sorted(tg.keys()):
        r, c = tiles.pos_from_name(tile)
        max_row = max(r, max_row)
        max_col = max(c, max_col)
        while r >= len(tiles_by_xy):
            tiles_by_xy.append([])
        while c >= len(tiles_by_xy[r]):
            tiles_by_xy[r].append([])
        tiles_by_xy[r][c].append(tile)

    # Top tiles
    is_odd = False
    for col in tiles_by_xy[0]:
        for tile in col:
            tt = tiles.type_from_fullname(tile)
            if not tt.startswith("SYSIO"):
                continue
            # Don't rename special or already-renamed tiles
            if tt[-1].isdigit():
                new_name = tile + ("_ODD" if is_odd else "_EVEN")
                assert new_name not in tg
                tg[new_name] = dict(tg[tile])
                tg[new_name]["tiletype"] = tg[new_name]["tiletype"] + ("_ODD" if is_odd else "_EVEN")
                del tg[tile]
            is_odd = not is_odd
    

    # Left/right tiles
    for tc in (0, max_col):
        is_odd = False
        bank = ""
        for row in tiles_by_xy:
            for tile in row[tc]:
                tt = tiles.type_from_fullname(tile)
                if not tt.startswith("SYSIO"):
                    continue
                if tt.endswith("REM"):
                    continue
                tile_bank = tt[tt.find("B")+1]
                if tile_bank != bank:
                    is_odd = False
                    bank = tile_bank
                if tt[-1].isdigit():
                    new_name = tile + ("_ODD" if is_odd else "_EVEN")
                    assert new_name not in tg
                    tg[new_name] = dict(tg[tile])
                    tg[new_name]["tiletype"] = tg[new_name]["tiletype"] + ("_ODD" if is_odd else "_EVEN")
                    del tg[tile]
                is_odd = not is_odd
    with open(tgp, "w") as outfile:
        json.dump({"tiles": tg}, outfile, sort_keys=True, indent=4)
