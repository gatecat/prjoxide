"""
Database and Database Path Management
"""
import logging
import os
from functools import lru_cache, cache
from os import path, makedirs
import json
import subprocess
from pathlib import Path
import pyron as ron
import gzip

def get_oxide_root():
    """Return the absolute path to the Project Oxide repo root"""
    return path.abspath(path.join(__file__, "../../../"))

def get_family_for_device(device):
    family = device.split('-')[0]
    if family == "LFD2NX":
        return "LIFCL"
    return family

def get_radiant_version():
    # `lapie` seems to be renamed every version or so. Map that out here. Most installations will have
    # the version name at the end of their path, so we just look at the radiant dir for a hint. The user
    # can override this setting with a RADIANTVERSION env variable
    known_versions = [ "2.2", "3.1", "2023", "2024", "2025" ]
    RADIANT_DIR = os.environ.get("RADIANTDIR")
    radiant_version= os.environ.get("RADIANTVERSION", None)

    if radiant_version is None:
        for version in known_versions:
            if RADIANT_DIR.find(version) > -1:
                radiant_version = version

    if radiant_version is None:
        radiant_version = "3.1"
    return radiant_version

def get_cache_dir():
    path = get_oxide_root() + "/.cache/" + get_radiant_version()
    makedirs(path, exist_ok=True)
    return path


def get_primitive_json(primitive):
    import parse_webdoc

    fn = get_cache_dir() + f"/primitives/{primitive}.json"

    primitives_dir = get_cache_dir() + f"/primitives/"
    if not path.exists(primitives_dir):
        os.makedirs(primitives_dir, exist_ok=True)

        RADIANT_DIR = os.environ.get("RADIANTDIR")
        html_dir = f"{RADIANT_DIR}/docs/webhelp/eng/Reference Guides/FPGA Libraries Reference Guide/"

        for file_path in Path(html_dir).iterdir():
            if file_path.is_file():
                print(file_path, primitives_dir)
                parse_webdoc.scrape_html(str(file_path), primitives_dir)

    with open(fn) as f:
        return json.load(f)

@cache
def get_db_root():
    """
    Return the path containing the Project Oxide database
    This is database/ in the repo, unless the `PRJOXIDE_DB` environment
    variable is set to another value.
    """
    if "PRJOXIDE_DB" in os.environ and os.environ["PRJOXIDE_DB"] != "":
        logging.info(f"Using external database path {os.environ['PRJOXIDE_DB']}")
        return os.environ["PRJOXIDE_DB"]
    else:
        return path.join(get_oxide_root(), "database")

def get_db_subdir(family = None, device = None, package = None):
    """
    Return the DB subdirectory corresponding to a family, device and
    package (all if applicable), creating it if it doesn't already
    exist.
    """
    subdir = get_db_root()
    if family is None and device is not None:
        family = get_family_for_device(device)

    dparts = [family, device, package]
    for dpart in dparts:
        if dpart is None:
            break
        subdir = path.join(subdir, dpart)
        if not path.exists(subdir):
            os.mkdir(subdir)
    return subdir

def get_base_addrs(family, device = None):
    if device is None:
        device = family
        family = get_family_for_device(device)

    tgjson = path.join(get_db_subdir(family, device), "baseaddr.json")
    if path.exists(tgjson):
        with open(tgjson, "r") as f:
            try:
                return json.load(f)["regions"]
            except:
                print(f"Exception encountered reading {tgjson}")
                raise
    return {}

@cache
def get_tilegrid(family, device = None):
    """
    Return the deserialised tilegrid for a family, device
    """
    if device is None:
        device = family
        family = get_family_for_device(device)

    tgjson = path.join(get_db_subdir(family, device), "tilegrid.json")
    if path.exists(tgjson):
        with open(tgjson, "r") as f:
            try:
                return json.load(f)
            except:
                print(f"Exception encountered reading {tgjson}")
                raise
    else:
        return {"tiles":{}}

def get_iodb(family, device = None):
    """
    Return the deserialised iodb for a family, device
    """
    if device is None:
        device = family
        family = get_family_for_device(device)
    tgjson = path.join(get_db_subdir(family, device), "iodb.json")
    with open(tgjson, "r") as f:
        return json.load(f)

@cache
def get_devices():
    """
    Return the deserialised content of devices.json
    """
    djson = path.join(get_db_root(), "devices.json")
    with open(djson, "r") as f:
        return json.load(f)

def get_tiletypes(family):
    family = get_family_for_device(family)
    p = path.join(get_db_root(), family, "tiletypes")

    tiletypes = {}

    if path.exists(p):
        for entry in Path(p).iterdir():
            if entry.name.endswith(".ron"):
                with open(entry.absolute(), "r") as f:
                    tiletypes[entry.name.split(".")[0]] = ron.loads(f.read().replace("\\'", "'"))

    return tiletypes
            

def get_db_commit():
    return subprocess.getoutput('git -C "{}" rev-parse HEAD'.format(get_db_root()))

@cache
def get_sites(family, device = None):
    import lapie

    if device is None:
        device = family
        family = get_family_for_device(family)

    return lapie.get_sites_with_pin(device)

def check_tiletype(tiletype, tiletype_info):
    pips = tiletype_info["pips"]
    enums = tiletype_info["enums"]
    words = tiletype_info["words"]
    
    for to_pin in pips:
        for from_pin in pips[to_pin]:
            if "bits" not in from_pin:
                wire = from_pin["from_wire"]
                print(f"Warning: Unmapped pip {wire} -> {to_pin}")

    for enum in enums:
        for option in enums[enum]["options"]:
            if len(enums[enum]["options"][option]) == 0:
                print(f"Warning unmapped option {option} in {enum}")

    for word in words:
        idx = 0
        for bit in words[word]["bits"]:
            if len(bit):
                print(f"Warning word entry for value {idx} in {word}")
            idx = idx + 1
            


def check_device(device):
    tiletypes = get_tiletypes(device)    
    tg = get_tilegrid(device)["tiles"]

    warned = set()
    
    for tile, tile_info in tg.items():
        tiletype = tile_info["tiletype"]

        if tiletype not in tiletypes and tiletype not in warned:
            warned.add(tiletype)            
            print(f"Warning: Could not find tile type definition for tiletype {tiletype} tile {tile} in {device}")

def get_device_list():
    devices = get_devices()

    for family in devices["families"]:
        for device in devices["families"][family]["devices"]:
            yield device


            
def check_consistency():
    devices = get_devices()

    for family in devices["families"]:
        
        tiletypes = get_tiletypes(family)

        for tiletype in tiletypes:
            check_tiletype(tiletype, tiletypes[tiletype])

        for device in devices["families"][family]["devices"]:
            check_device(device)
           
