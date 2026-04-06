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
import logging
import sys, os, shutil, hashlib, gzip
import time
from logging import exception
from pathlib import Path

root_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
cache_dir = os.path.join(root_dir, ".bitstreamcache")

def get_version_directory():
    radiantdir = os.environ.get("RADIANTDIR", "UNKNOWN")
    return Path(radiantdir).name + "-" + hashlib.md5(radiantdir.encode("UTF-8")).hexdigest()

version_directory = get_version_directory()

def get_hash_by_contents(device, input_file_contents, env = None):
    if env is None:
        env = os.environ

    hasher = hashlib.sha1()
    hasher.update(b"DEVICE")
    hasher.update(device.encode('utf-8'))
    for envkey in ("GEN_RBF", "DEV_PACKAGE", "SPEED_GRADE", "STRUCT_VER", "RBK_MODE"):
        if envkey in env:
            hasher.update(envkey.encode('utf-8'))
            hasher.update(env[envkey].encode('utf-8'))
    for fn,contents in input_file_contents.items():
        ext = os.path.splitext(fn)[1]
        hasher.update("input{}".format(ext).encode('utf-8'))
        hasher.update(contents)

    # Split into chunks since some file systems don't scale well with giant flat dirs
    h = hasher.hexdigest()
    h_prefix = h[:2]
    h_remaining = h[2:]
    logging.debug(f"Hash lookup gave {h}")
    return (h_prefix, h_remaining)

def get_hash(device, input_files, env = None):
    input_file_contents = {
        fname: open(fname,"rb").read()
        for fname in input_files
    }

    return get_hash_by_contents(device, input_file_contents, env=env)

def fetch_by_contents(device, input_file_contents, env = None):
    if not os.path.exists(cache_dir):
        return

    h = get_hash_by_contents(device, input_file_contents, env=env)

    check_dirs = [os.path.join(cache_dir, version_directory, *h),
                  os.path.join(cache_dir, "".join(h))]

    for cache_entry in check_dirs:
        if not os.path.exists(cache_entry) or len(os.listdir(cache_entry)) < 2:
            continue

        # Touch the directory and it's contents
        now = time.time()
        os.utime(cache_entry, (now, now))
        products = os.listdir(cache_entry)
        for outprod in products:
            gz_path = os.path.join(cache_entry, outprod)
            os.utime(gz_path, (now, now))

            yield (outprod, gz_path)

        if len(products):
            return


def fetch(device, input_files, env = None):
    if not os.path.exists(cache_dir):
        return

    input_file_contents = {
        fname:open(fname, "rb").read()
        for fname in input_files
    }

    return fetch_by_contents(device, input_file_contents, env)

def main():
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

        cache_entries = fetch(sys.argv[2], sys.argv[4:])

        for (outprod, gz_path) in cache_entries:
            assert gz_path.endswith(".gz")

            Path(gz_path).touch()
            if gz_path.endswith(".bit.gz"):
                print(f"Linking {os.path.join(sys.argv[3], outprod)}")
                os.symlink(gz_path, os.path.join(sys.argv[3], outprod))
            else:
                bn = Path(gz_path[:-3]).name
                with gzip.open(gz_path, 'rb') as gzf:
                    print(f"Writing {os.path.join(sys.argv[3], bn)}")
                    with open(os.path.join(sys.argv[3], bn), 'wb') as outf:
                        outf.write(gzf.read())
        else:
            sys.exit(1)

        sys.exit(0)

    if cmd == "commit":
        if not os.path.exists(cache_dir):
            sys.exit(0)
        idx = sys.argv.index("output")
        if len(sys.argv) < 6 or idx == -1:
            print("Usage: tools/bitstreamcache.py commit <DEVICE> <INPUT FILE 1> <INPUT FILE 2> output <OUTPUT FILE 1> ..")
            sys.exit(1)
        h = get_hash(sys.argv[2], sys.argv[3:idx])

        cache_entry = os.path.join(cache_dir, version_directory, *h)
        if not os.path.exists(cache_entry):
            os.makedirs(cache_entry, exist_ok=True)
        for outprod in sys.argv[idx+1:]:
            bn = os.path.basename(outprod)
            cn = os.path.join(cache_entry, bn + ".gz")

            if not os.path.exists(outprod):
                raise Exception(f"Output product does not exist")

            if os.path.getsize(outprod) == 0:
                raise Exception(f"Output product has zero length; refusing to gzip {outprod}")

            with gzip.open(cn, 'wb') as gzf:
                with open(outprod, 'rb') as inf:
                    gzf.write(inf.read())
        sys.exit(0)

if __name__ == "__main__":
    main()