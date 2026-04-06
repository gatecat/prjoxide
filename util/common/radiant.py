"""
Python wrapper for `radiant.sh`
"""
import asyncio
import logging
import time
from os import path
import os
import subprocess
import database
import sys

class RadiantRunError(Exception):
    def __init__(self, message, error_lines):
        self.message = message
        self.error_lines = error_lines
        super().__init__(self.message)


def run_bash_script(env, *args, cwd = None, stdout = subprocess.PIPE, stderr = subprocess.PIPE):
    slug = " ".join(args[1:])
    logging.debug("Running script: %s", slug)

    subprocess_args = {
        "args": ["bash", *args],
        "env":  env,
        "cwd": cwd,
        "stdout": stdout,
        "stderr": stderr
    }

    def process_subprocess_result(stdout, stderr, returncode):
        show_output = returncode != 0 or len(stderr.strip()) > 0

        error_lines = []

        if show_output or logging.DEBUG >= logging.root.level:
            for stream in [("", stdout, sys.stdout), ("ERR:", stderr, sys.stdout)]:
                if stream[1] is not None:
                    for l in stream[1].decode().splitlines():
                        if l.startswith("ERROR - "):
                            error_lines.append(l)
                        logging.info(f"[{stream[0]} {slug}] {l}")


        if returncode != 0:
            raise RadiantRunError(f"Error encountered running radiant: {slug} {returncode} cwd: {cwd}", error_lines)

    # try:
    #     loop = asyncio.get_running_loop()
    #
    #     async def async_function():
    #         proc = await asyncio.create_subprocess_exec(**subprocess_args)
    #
    #         stdout, stderr = await proc.communicate()
    #
    #         process_subprocess_result(stdout, stderr, await proc.wait())
    #
    #         return proc
    #
    #     return asyncio.run_coroutine_threadsafe(async_function(), loop).result()
    # except RuntimeError:
    #     pass


    proc = subprocess.run(**subprocess_args)

    process_subprocess_result(proc.stdout, proc.stderr, proc.returncode)

    return proc


def run(device, source, struct_ver=True, raw_bit=False, pdcfile=None, rbk_mode=False):
    """
    Run radiant.sh with a given device name and source Verilog file
    """
    env = os.environ.copy()
    if struct_ver:
        env["STRUCT_VER"] = "1"
    if raw_bit:
        env["GEN_RBT"] = "1"
    if rbk_mode:
        env["RBK_MODE"] = "1"

    dsh_path = path.join(database.get_oxide_root(), "radiant.sh")
    logging.info(f"Building [{device}] {source}")
    return run_bash_script(env, dsh_path, device, source)

async def partition_wire_list(cfg, wires, prefix=""):
    import interconnect
    wires = sorted(set(wires))
    try:
        t = time.time()
        await asyncio.to_thread(interconnect.create_wires_file, cfg, wires, prefix=prefix)
        # interconnect.create_wires_file(cfg, wires, prefix = f"{idx}/{len(wires)}/")
        print(f"Built file with {len(wires)} {time.time() - t} seconds {len(wires) / (time.time() - t)} wires.")

        return wires, [], []
    except RadiantRunError as e:
        for l in e.error_lines:
            if "No arc found for" in l:
                (to_wire, from_wire) = l.split(" ")[-1].split(".")
                idx = wires.index((from_wire, to_wire))
                return wires[:idx], [ wires[idx] ], wires[(idx+1):]
        raise e

async def validate_wire_list(cfg, wires, prefix="", max_wires=100000):
    def chunkify(lst, n):
        return [lst[i::n] for i in range(n)]

    bad_arcs = []
    while len(wires):
        chunks = 10
        if len(wires) // chunks > max_wires:
            chunks = len(wires) // (max_wires - 1)

        partitions = await asyncio.gather(
            *[asyncio.create_task(partition_wire_list(cfg, grp, f"{(len(wires) // chunks * i)}/")) for i, grp in enumerate(chunkify(wires, chunks))])

        wires = []
        for (good, bad, unknown) in partitions:
            bad_arcs.extend(bad)
            wires.extend(unknown)

    return bad_arcs

