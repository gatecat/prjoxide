#!/usr/bin/env python3
"""
This script reads the output from Lattice's bstool in "test" mode, which should be invoked thus:

```
bstool -t bitstream.bit > bitstream.test
```

and from it obtains a list of tiles with the following information:
    - Tile name (with position encoded in the name)
    - Tile type
    - Frame and bit offset
    - Bitstream size in bits ("rows") and frames ("cols")
and creates a JSON file as output
"""

import sys, re
import json, argparse

tile_re = re.compile(
    r'^Tile\s+([A-Z0-9a-z_/]+)\s+\((\d+), (\d+)\)\s+bitmap offset\s+\((\d+), (\d+)\)\s+\<([A-Z0-9a-z_/]+)>\s*$')
end_digit_re = re.compile(
    r'(\d+)$')

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('infile', type=argparse.FileType('r'),
                    help="input file from bstool")
parser.add_argument('outfile', type=argparse.FileType('w'),
                    help="output JSON file")

rc_re = re.compile(r'R(\d+)C(\d+)')

# For some reason TAP tiles don't have a column in their name. Restore them,
# using locations determined from Radiant physical view (for now)
tap_frame_to_col = {
    16: 14,
    22: 38,
    28: 62,
    34: 74
}

def main(argv):
    args = parser.parse_args(argv[1:])
    tiles = {}
    current_tile = None
    for line in args.infile:
        tile_m = tile_re.match(line)
        if tile_m:
            name = tile_m.group(6)
            current_tile = {
                "tiletype": tile_m.group(1),
                "start_bit": int(tile_m.group(4)),
                "start_frame": int(tile_m.group(5)),
                "bits": int(tile_m.group(2)),
                "frames": int(tile_m.group(3)),
            }
            s =  rc_re.search(name)
            if not s:
                assert current_tile["start_frame"] in tap_frame_to_col
                # Regularise tile name for TAP tiles
                col = tap_frame_to_col[current_tile["start_frame"]]
                em = end_digit_re.search(name)
                row = int(em.group(1))
                name = "{}_R{}C{}".format(name[0:-len(em.group(1))], row, col)
                current_tile["row"] = row
                current_tile["col"] = col
            else:
                current_tile["row"] = int(s.group(1))
                current_tile["col"] = int(s.group(2))
            identifier = name + ":" + tile_m.group(1)
            assert identifier not in tiles
            tiles[identifier] = current_tile
    json.dump(tiles, args.outfile, sort_keys=True, indent=4)
    args.outfile.write("\n")
if __name__ == "__main__":
    main(sys.argv)
