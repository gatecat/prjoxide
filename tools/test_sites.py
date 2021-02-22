#!/usr/bin/env python3
"""
Convert the tile grid for a given family and device to HTML format
"""
import sys, re
import argparse
import database
import libpyprjoxide


def main(argv):
    db = libpyprjoxide.Database(database.get_db_root())
    libpyprjoxide.build_sites(db, "LIFCL-40", "PLC")

if __name__ == "__main__":
    main(sys.argv)
