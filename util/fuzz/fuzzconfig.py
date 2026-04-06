"""
This module provides a structure to define the fuzz environment
"""
import gzip
import hashlib
import json
import logging
import os
import pickle
import threading
from collections import defaultdict
from concurrent.futures import Future
from functools import cache
from multiprocessing.synchronize import RLock
from os import path
from pathlib import Path
from string import Template
import radiant
import database
import libpyprjoxide
import cachecontrol

#db = None

class LockedObject:
    def __init__(self, obj):
        self.obj = obj
        self.lock = threading.Lock()

    def __enter__(self):
        self.lock.acquire()
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

_db_lock = None

def db_lock():
    global _db_lock
    if _db_lock is None:
        db = libpyprjoxide.Database(database.get_db_root())
        _db_lock = LockedObject(db)

    return _db_lock



PLATFORM_FILTER = os.environ.get("FUZZER_PLATFORM", None)

_platform_skip_warnings = set()
def should_fuzz_platform(device):
    if PLATFORM_FILTER is not None and PLATFORM_FILTER not in device:
        if device not in _platform_skip_warnings:
            logging.warning(f"FUZZER_PLATFORM set to {PLATFORM_FILTER}, skipping {device}")
        _platform_skip_warnings.add(device)
        return False
    return True

def devices_to_fuzz():
    families = database.get_devices()["families"]

    return sorted([
        device
        for family in families
        for device in families[family]["devices"]
        if should_fuzz_platform(device)
    ])


@cache
def get_baseline_chip(baseline):
    with db_lock() as db:
        logging.info(f"Loading {baseline}")
        return libpyprjoxide.Chip.from_bitstream(db, baseline)

def find_baseline_differences_hash_fn(args, kwds):
    device = kwds["device"]
    baseline = kwds.get("baseline", None)
    if baseline is None:
        baseline = FuzzConfig.standard_empty(device)

    kwds["active_bitstream"] = hashlib.sha1(open(kwds["active_bitstream"].bitstream, 'br').read()).hexdigest()
    kwds["baseline"] = hashlib.sha1(open(baseline.bitstream, 'br').read()).hexdigest()

    sorted_kwargs = sorted(kwds.items())

    serialized = pickle.dumps(sorted_kwargs)
    return hashlib.sha256(serialized).hexdigest()

@cachecontrol.cache_fn(find_baseline_differences_hash_fn)
def find_baseline_differences(device, active_bitstream, ignore_tiles=set(), baseline = None):
    import tiles

    if baseline is None:
        baseline = FuzzConfig.standard_empty(device)

    baseline_chip = get_baseline_chip(baseline.bitstream)
    with db_lock() as db:
        deltas, ip_values = baseline_chip.delta_with_ipvalues(db, active_bitstream.bitstream)
        ip_values = [(a, v) for a, v in ip_values if v != 0]

    filtered_deltas = {k: v for k, v in deltas.items() if k not in ignore_tiles}

    return filtered_deltas, ip_values

@cache
def read_design_template(des_template):
    with open(des_template, "r") as inf:
        return inf.read()

class BitstreamInfo:
    def __init__(self, config, bitstream_file, vfiles):
        self.config = config
        assert isinstance(bitstream_file, str)
        self.bitstream = bitstream_file
        self.vfiles = vfiles

    def __str__(self):
        return f"BitstreamInfo: {self.bitstream}"


class FuzzConfig:
    _standard_empty_bitfile = {}
    radiant_cache_hits = 0
    radiant_builds = 0
    delta_skips = 0

    def __init__(self, device, job, tiles=[], sv = None):
        """
        :param job: user-friendly job name, used for folder naming etc
        :param device: Target device name
        :param tiles: List of tiles to consider during fuzzing
        :param sv: Minimal structural Verilog file to use as a base for interconnect fuzzing
        """
        self.device = device
        self.job = job
        self.tiles = tiles
        if sv is None:
            family = database.get_family_for_device(device)
            suffix = device.split("-")[1]
            sv = database.get_oxide_root() + f"/fuzzers/{family}/shared/empty.v"
        self.sv = sv
        self.rbk_mode = True if self.device == "LFCPNX-100" or self.device == "LIFCL-33U" else False
        self.struct_mode = True
        self.udb_specimen = None

    @staticmethod
    @cache
    def standard_empty(device):
        if device not in FuzzConfig._standard_empty_bitfile:
            cfg = FuzzConfig(job=f"standard-empty-file", device=device, tiles=[])
            FuzzConfig._standard_empty_bitfile[device] = cfg.build_design(cfg.sv, {}, prefix="baseline/")
            pass
        return FuzzConfig._standard_empty_bitfile[device]

    @staticmethod
    @cache
    def standard_chip(device):
        with db_lock() as db:
            baseline = FuzzConfig.standard_empty(device)
            return libpyprjoxide.Chip.from_bitstream(db, baseline.bitstream)

    @property
    def workdir(self):
        return path.join(database.get_oxide_root(), "work", Path(os.getcwd()).name, self.device, self.job)

    def make_workdir(self):
        """Create the working directory for this job, if it doesn't exist already"""
        os.makedirs(self.workdir, exist_ok=True)

    def delta_dir(self):
        db_dir = os.environ.get("PRJOXIDE_DB", None)
        if db_dir is not None:
            db_name = Path(db_dir).name
            return f".deltas/{db_name}/{self.device}"

        return f".deltas/{self.device}"

    def serialize_deltas(self, fz, prefix = ""):
        name = f"{self.delta_dir()}/{self.job}/{prefix}"
        os.makedirs(Path(name).parent, exist_ok=True)
        fz.serialize_deltas(name)

    def check_deltas(self, name):
        if os.path.exists(f"{self.delta_dir()}/{self.job}/{name}.ron"):
            logging.debug(f"Delta exists for {name} {self.job} {self.device}; skipping")
            FuzzConfig.delta_skips = FuzzConfig.delta_skips + 1
            return True
        logging.debug(f"{self.delta_dir()}/{self.job}/{name}.ron miss")
        return False

    def solve(self, fz, db):
        try:
            fz.solve(db)
            self.serialize_deltas(fz, fz.get_name())
        except:
            self.serialize_deltas(fz, f"{fz.get_name()}-FAILED")
            raise

    def setup(self, skip_specimen=False):
        """
        Create a working directory, and run Radiant on a minimal Verilog file to create a udb for Tcl usage etc
        """

        # Load the global database if it doesn't exist already

        self.make_workdir()
        if not skip_specimen:
            self.build_design(self.sv, {})

    def subst_defaults(self):
        packages = {
            "LIFCL-33": "WLCSP84",
            "LIFCL-33U": "WLCSP84",
            "LFD2NX-40": "CABGA256",
            "LFCPNX-40": "LFG672",
            "LFCPNX-100": "LFG672"
        }

        return {
            "arch": self.device.split("-")[0],
            "arcs_attr": "",
            "device": self.device,
            "package": packages.get(self.device, "QFN72"),
            "speed_grade": "8" if self.device == "LIFCL-33" else "7"
        }

    def build_design_future(self, executor, *args, **kwargs):
        future = executor.submit(self.build_design, *args, **kwargs)
        future.name = f"Build {self.device}"
        future.executor = executor
        return future

    def build_design(self, des_template, substitutions = {}, prefix="", substitute=True, executor = None):
        assert ' ' not in prefix
        """
        Run Radiant on a given design template, applying a map of substitutions, plus some standard substitutions
        if not overriden.

        :param des_template: path to template (structural) Verilog file
        :param substitutions: dictionary containing template subsitutions to apply to Verilog file
        :param prefix: prefix to append to filename, for running concurrent jobs without collisions

        Returns the path to the output bitstream
        """
        subst = dict(substitutions)

        prefix = f"{threading.get_ident()}/{prefix}/"

        subst_defaults = self.subst_defaults()

        subst = subst_defaults | subst

        os.makedirs(path.join(self.workdir, prefix), exist_ok=True)
        desfile = path.join(self.workdir, prefix + "design.v")

        bitfile = path.join(self.workdir, prefix + "design.bit")
        bitfile_gz = path.join(self.workdir, prefix + "design.bit.gz")
        logging.debug(f"Building {des_template} with subs {substitutions} into {desfile}")

        if "sysconfig" in subst:
            pdcfile = path.join(self.workdir, prefix + "design.pdc")
            with open(pdcfile, "w") as pdcf:
                pdcf.write("ldc_set_sysconfig {{{}}}\n".format(subst["sysconfig"]))

        for bf in [bitfile, bitfile_gz]:
            if path.exists(bf):
                os.remove(bf)

        template_contents = read_design_template(des_template)

        with open(desfile, "w") as ouf:
            if substitute:
                ouf.write(Template(template_contents).substitute(**subst))
            else:
                ouf.write(template_contents)

        env = os.environ.copy()
        if self.struct_mode:
            env["STRUCT_VER"] = "1"
        if self.rbk_mode:
            env["RBK_MODE"] = "1"

        needs_udb = self.struct_mode and self.udb_specimen is None

        import bitstreamcache
        cached_result = bitstreamcache.fetch(self.device, [desfile], env=env)
        foundFile = None
        for (outprod, gzfile) in cached_result:
            if gzfile.endswith(".bit.gz"):
                FuzzConfig.radiant_cache_hits = FuzzConfig.radiant_cache_hits + 1
                foundFile = gzfile
            elif needs_udb and gzfile.endswith(".udb.gz"):
                with gzip.open(gzfile, 'rb') as gzf:
                    self.udb_specimen = path.join(self.workdir, prefix, "par.udb")
                    Path(self.udb_specimen).parent.mkdir(parents=True, exist_ok=True)
                    with open(self.udb_specimen, 'wb') as outf:
                        outf.write(gzf.read())

        if foundFile is not None:
            rtn = BitstreamInfo(self, foundFile, desfile)
            if executor is not None:
                f = Future()
                f.set_result(rtn)
                return f
            return rtn

        def run_radiant_sh():
            FuzzConfig.radiant_builds = FuzzConfig.radiant_builds + 1
            process_results = radiant.run(self.device, desfile, struct_ver=self.struct_mode, raw_bit=False, rbk_mode=self.rbk_mode)

            error_output = process_results.stderr.decode().strip()
            if "ERROR <" in error_output:
                raise Exception(f"Error found during bitstream build: {error_output} (Args: {self.device} {desfile})")

            if self.struct_mode and self.udb_specimen is None:
                self.udb_specimen = path.join(self.workdir, prefix + "design.tmp", "par.udb")
            if path.exists(bitfile):
                return BitstreamInfo(self, bitfile, desfile)
            if path.exists(bitfile_gz):
                return BitstreamInfo(self, bitfile_gz, desfile)

            raise Exception(f"Could not generate bitstream file {bitfile} {bitfile_gz}")

        if executor is None:
            return run_radiant_sh()

        return executor.submit(run_radiant_sh)


    @property
    def udb(self):
        """
        A udb file specimen for Tcl
        """
        if self.udb_specimen is None:
            self.setup()
        assert self.udb_specimen is not None
        return self.udb_specimen

def json_converter(obj):
    if isinstance(obj, set):
        return sorted(obj)
    raise TypeError

def stablehash(x):
    bytes_data = json.dumps(x, sort_keys=True, default=json_converter).encode('utf-8')

    hasher = hashlib.new("sha1")
    hasher.update(bytes_data)

    return hasher.hexdigest()

def make_overlay_name(k):
    if isinstance(k, str):
        return k

    (anon_pips, *args) = k
    return "-".join([*args, stablehash(anon_pips)])

def register_device_overlays(device, overlay_provider, overlays):
    tiles_to_overlays = {}
    for k, lst in overlays.items():
        for item in lst:
            if item not in tiles_to_overlays:
                tiles_to_overlays[item] = {item.split(":")[-1]}
            tiles_to_overlays[item].add("overlays/" + make_overlay_name(k))

    overlays_to_tiles = defaultdict(set)
    for tile, tile_overlays in tiles_to_overlays.items():
        overlays_to_tiles[tuple(sorted(tile_overlays))].add(tile)

    db_sub_dir = database.get_db_subdir(device=device)
    os.makedirs(f"{db_sub_dir}/overlays.d", exist_ok = True)
    with open(f"{db_sub_dir}/overlays.d/{overlay_provider}.json", "w") as f:
        overlay_doc = {
            "overlays": {
                stablehash(k): sorted(k) for k in overlays_to_tiles
            },
            "tiletypes": {
                stablehash(k): sorted(v) for k, v in overlays_to_tiles.items()
            }
        }

        json.dump(overlay_doc, f, default=json_converter, indent=4, sort_keys=True)
