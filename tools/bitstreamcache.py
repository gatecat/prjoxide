#!/usr/bin/env python3
"""
Bitstream cache tool for prjoxide

This avoids expensive bitstream rebuilds when making small changes to the
fuzzer and the Verilog input is largely unchanged.

Note that it is disabled by default. Run:
    tools/bitstreamcache.py init
to start using it.

Usage:
    tools/bitstreamcache.py fetch <DEVICE> <OUTPUT DIR> <INPUT FILE 1> <INPUT FILE 2> ...
        if a bitstream with the given configuration and input already exists,
        copy the products to <OUTPUT DIR> and return 0. Otherwise return 1.

    tools/bitstreamcache.py commit <DEVICE> <INPUT FILE 1> <INPUT FILE 2> output <OUTPUT FILE 1> ..
        save output files as the products of the input files and configuration

gzip and gunzip must be on your path for it to work

"""

import sys, os, shutil, hashlib, gzip

root_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
cache_dir = os.path.join(root_dir, ".bitstreamcache")

def get_hash(device, input_files):
    hasher = hashlib.sha1()
    hasher.update(b"DEVICE")
    hasher.update(device.encode('utf-8'))
    for envkey in ("GEN_RBF", "DEV_PACKAGE", "SPEED_GRADE", "STRUCT_VER"):
        if envkey in os.environ:
            hasher.update(envkey.encode('utf-8'))
            hasher.update(os.environ[envkey].encode('utf-8'))
    for fname in input_files:
        ext = os.path.splitext(fname)[1]
        hasher.update("input{}".format(ext).encode('utf-8'))
        with open(fname, "rb") as f:
            hasher.update(f.read())
    return hasher.hexdigest()

if len(sys.argv) < 2:
    print("Expected command (init|fetch|commit)")
    sys.exit(1)
cmd = sys.argv[1]
if cmd == "init":
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
if cmd == "fetch":
    if not os.path.exists(cache_dir):
        sys.exit(1)
    if len(sys.argv) < 5:
        print("Usage: tools/bitstreamcache.py fetch <DEVICE> <OUTPUT DIR> <INPUT FILE 1> <INPUT FILE 2> ...")
        sys.exit(1)
    h = get_hash(sys.argv[2], sys.argv[4:])
    print(h)
    cache_entry = os.path.join(cache_dir, h)
    if not os.path.exists(cache_entry) or len(os.listdir(cache_entry)) == 0:
        sys.exit(1)
    for outprod in os.listdir(cache_entry):
        bn = outprod
        assert bn.endswith(".gz")
        bn = bn[:-3]
        with gzip.open(os.path.join(cache_entry, outprod), 'rb') as gzf:
            with open(os.path.join(sys.argv[3], bn), 'wb') as outf:
                outf.write(gzf.read())
    sys.exit(0)
if cmd == "commit":
    if not os.path.exists(cache_dir):
        sys.exit(0)
    idx = sys.argv.index("output")
    if len(sys.argv) < 6 or idx == -1:
        print("Usage: tools/bitstreamcache.py commit <DEVICE> <INPUT FILE 1> <INPUT FILE 2> output <OUTPUT FILE 1> ..")
        sys.exit(1)
    h = get_hash(sys.argv[2], sys.argv[3:idx])
    cache_entry = os.path.join(cache_dir, h)
    if not os.path.exists(cache_entry):
        os.mkdir(cache_entry)
    for outprod in sys.argv[idx+1:]:
        bn = os.path.basename(outprod)
        cn = os.path.join(cache_entry, bn + ".gz")
        with gzip.open(cn, 'wb') as gzf:
            with open(outprod, 'rb') as inf:
                gzf.write(inf.read())
    sys.exit(0)
