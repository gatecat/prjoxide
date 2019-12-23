"""
Python wrapper for `radiant.sh`
"""
from os import path
import os
import subprocess
import database


def run(device, source, struct_ver=True, raw_bit=False):
    """
    Run radiant.sh with a given device name and source Verilog file
    """
    env = os.environ.copy()
    if struct_ver:
        env["STRUCT_VER"] = "1"
    if raw_bit:
        env["GEN_RBT"] = "1"
    dsh_path = path.join(database.get_oxide_root(), "radiant.sh")
    return subprocess.run(["bash",dsh_path,device,source], env=env)
