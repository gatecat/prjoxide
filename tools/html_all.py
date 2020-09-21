#!/usr/bin/env python3
"""
Project Oxide Master HTML Generation Script

Usage:
html_all.py <output_folder>
"""

import os, sys, time
from os import path
from string import Template
import argparse
import database
import html_tilegrid
import html_tilebits
import fuzzloops
import glob
import libpyprjoxide

oxide_docs_index = """
<html>
<head>
<title>Project Oxide HTML Documentation</title>
</head>
<body>
<h1>Project Oxide HTML Documentation</h1>
<p>Project Oxide is a project to document the Lattice Nexus (28nm) devices bitstream and internal architecture.</p>
<p>This repository contains HTML documentation automatically generated from the
<a href="https://github.com/daveshah1/prjoxide">Project Oxide</a> database. The equivalent
machine-readable data is located in <a href="https://github.com/daveshah1/prjoxide-db">prjoxide-db.<a/>
Data generated includes tilemap data and bitstream data for some basic tile types. Click on any tile to see its bitstream
documentation.
</p>
<p>This HTML documentation was generated at ${datetime}</p>
<hr/>
<h3>General Documentation</h3>
<ul>
$gen_docs_toc
</ul>
<hr/>
$docs_toc
<hr/>
<p>Licensed under a very permissive <a href="COPYING">CC0 1.0 Universal</a> license.</p>
</body>
</html>
"""

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('fld', type=str,
                    help="output folder")


def generate_device_docs(family, device, folder):
    html_tilegrid.main(["html_tilegrid", family, device, path.join(folder, "index.html"), path.join(folder, "regions.html")])

def generate_tile_docs(family, device, tile, folder):
    html_tilebits.main(["html_tilebits", family, device, tile, folder])


def get_device_tiles(family, devices):
    all_tiles = set()
    fd_tiles = {}
    for dev, devdata in sorted(devices.items()):
        if devdata["fuzz"]:
            fd_tiles[family, dev] = []
            for tilename, tiledata in sorted(database.get_tilegrid(family, dev)["tiles"].items()):
                tt = tiledata["tiletype"]
                if tt not in all_tiles:
                    all_tiles.add(tt)
                    fd_tiles[family, dev].append(tt)
    return fd_tiles


def main(argv):
    args = parser.parse_args(argv[1:])
    if not path.exists(args.fld):
        os.mkdir(args.fld)
    commit_hash = database.get_db_commit()
    build_dt = time.strftime('%Y-%m-%d %H:%M:%S')
    gen_docs_toc = ""
    gdir = path.join(args.fld, "general")
    if not path.exists(gdir):
        os.mkdir(gdir)
    for mdfile in glob.glob(path.join(database.get_oxide_root(), "docs", "general", "*.md")):
        with open(mdfile, "r") as f:
            if f.read(1) != "#":
                continue
            title = f.readline().strip()
        htmlfn = path.basename(mdfile).replace(".md", ".html")
        htmlfile = path.join(gdir, htmlfn)
        with open(htmlfile, "w") as f:
            f.write(libpyprjoxide.md_file_to_html(mdfile))
        gen_docs_toc += '<li><a href="general/{}">{}</a></li>\n'.format(htmlfn, title)
    docs_toc = ""
    for fam, fam_data in sorted(database.get_devices()["families"].items()):
        fdir = path.join(args.fld, fam)
        if not path.exists(fdir):
            os.mkdir(fdir)
        thdir = path.join(fdir, "tilehtml")
        if not path.exists(thdir):
            os.mkdir(thdir)
        bhdir = path.join(fdir, "belhtml")
        if not path.exists(bhdir):
            os.mkdir(bhdir)
        docs_toc += "<h3>{} Family</h3>".format(fam)
        docs_toc += "<h4>Generated Bitstream Documentation</h4>"
        docs_toc += "<ul>"
        tiles = get_device_tiles(fam, fam_data["devices"])
        for dev, devdata in sorted(fam_data["devices"].items()):
            if devdata["fuzz"]:
                ddir = path.join(fdir, dev)
                if not path.exists(ddir):
                    os.mkdir(ddir)
                print("********* Generating documentation for device {}".format(dev))
                generate_device_docs(fam, dev, ddir)
                if (fam, dev) in tiles:
                    for tile in tiles[fam, dev]:
                        print("*** Generating documentation for tile {}".format(tile))
                        generate_tile_docs(fam, dev, tile, fdir)
                docs_toc += '<li><a href="{}">{} Documentation</a></li>'.format(
                    '{}/{}/index.html'.format(fam, dev),
                    dev
                )

        docs_toc += "</ul>"

    index_html = Template(oxide_docs_index).substitute(
        datetime=build_dt,
        commit=commit_hash,
        docs_toc=docs_toc,
        gen_docs_toc=gen_docs_toc,
    )
    with open(path.join(args.fld, "index.html"), 'w') as f:
        f.write(index_html)


if __name__ == "__main__":
    main(sys.argv)
