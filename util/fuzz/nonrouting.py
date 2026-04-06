"""
Utilities for fuzzing non-routing configuration. This is the counterpart to interconnect.py
"""
import logging
import threading
import tiles
import libpyprjoxide

import fuzzconfig
import fuzzloops
import os
from interconnect import transaction_log
from DesignFileBuilder import BitConflictException

from primitives import EnumSetting

def fuzz_intval(vec):
    x = 0
    for i, b in enumerate(vec):
        if b:
            x |= (1 << i)
    return x

def fuzz_word_setting(config, name, length, get_sv_substs, desc="", overlay="", executor = None):
    """
    Fuzz a multi-bit setting, such as LUT initialisation

    :param config: FuzzConfig instance containing target device and tile of interest
    :param name: name of the setting to store in the database
    :param length: number of bits in the setting
    :param get_sv_substs: a callback function, that is called with an array of bits to create a design with that setting
    """
    if not fuzzconfig.should_fuzz_platform(config.device):
        return

    if config.check_deltas(name):
        return

    with fuzzloops.Executor(executor) as executor:
        prefix = f"{name}/"

        baseline = config.build_design_future(executor, config.sv, get_sv_substs([False for _ in range(length)]), prefix + "baseline/")

        bitstream_futures = [
            config.build_design_future(executor, config.sv, get_sv_substs([(_ == i) for _ in range(length)]),
                            prefix + f"{i}/")
            for i in range(length)
        ]

        def integrate_bitstreams(bitstreams):
            baseline = bitstreams[0]
            bitstreams = bitstreams[1:]
            with fuzzconfig.db_lock() as db:
                fz = libpyprjoxide.Fuzzer.word_fuzzer(db, baseline.bitstream, set(config.tiles), name, desc, length,
                                                      baseline.bitstream, overlay=overlay)
                for i in range(length):
                    fz.add_word_sample(db, i, bitstreams[i].bitstream)

                try:
                    config.solve(fz, db)
                except BaseException as e:
                    logging.exception(
                        f"Exception {e} while adding word sample {i} from {[b.vfiles for b in bitstreams]} vs {baseline.vfiles}")
                    raise

        return fuzzloops.chain([baseline, *bitstream_futures], f"Word {config.device}", integrate_bitstreams)

def fuzz_enum_setting(config, empty_bitfile, name, values, get_sv_substs, include_zeros=False,
                      assume_zero_base=False, min_cover={}, desc="", mark_relative_to=None, executor = None, overlay=""):
    """
    Fuzz a setting with multiple possible values

    :param config: FuzzConfig instance containing target device and tile of interest
    :param empty_bitfile: a baseline empty bitstream to diff against
    :param name: name of the setting to store in the database
    :param values: list of values taken by the enum
    :param get_sv_substs: a callback function, 
    :param include_zeros: if set, bits set to zero are not included in db. Needed for settings such as CEMUX which share
    bits with routing muxes to prevent conflicts.
    :param assume_zero_base: if set, the baseline bitstream is considered the all-zero bitstream
    :param min_cover: for each setting in this, run with each value in the array that setting points to, to get a minimal
    bit set
    """

    assert len(values) > 1, f"Enum setting {name} requires more than one option (given {values})"

    if not fuzzconfig.should_fuzz_platform(config.device):
        return

    if config.check_deltas(name):
        return

    with fuzzloops.Executor(executor) as executor:
        futures = []

        def integrate_build(subs, prefix, opt_name):
            bitstream = config.build_design(config.sv, subs, prefix.replace(" ", ""))
            return (opt_name, bitstream)

        for opt in values:
            opt_name = opt
            if opt == "#SIG" and name.endswith("MUX"):
                opt_name = name[:-3].split(".")[1]
            if opt == "#INV":
                opt_name = "INV"

            if opt in min_cover:
                for c in min_cover[opt]:
                    futures.append(executor.submit(integrate_build, get_sv_substs((opt, c)), f"cover/{name}/{opt}/{c}", opt_name))
            else:
                futures.append(executor.submit(integrate_build, get_sv_substs(opt), f"{name}/{opt}/", opt_name))
        for future in futures:
            future.name = f"Build enum design"

        def integrate_bitstreams(bitstreams):
            with fuzzconfig.db_lock() as db:
                fz = libpyprjoxide.Fuzzer.enum_fuzzer(db, empty_bitfile.bitstream, set(config.tiles), name, desc,
                                                      include_zeros, assume_zero_base,
                                                      mark_relative_to=mark_relative_to, overlay=overlay)

                for idx, (opt, bitstream) in enumerate(bitstreams):
                    logging.debug(f"Enum sample for {name}={opt} with {bitstream.bitstream} {bitstream.vfiles}")
                    transaction_log.info(f"add_enum_sample {config.device}: {name} {opt} Files: {bitstream.vfiles}")

                    fz.add_enum_sample(db, opt, bitstream.bitstream)

                try:
                    config.solve(fz, db)
                except BaseException as e:
                    logging.error(f"Enum sample error for {name} with {bitstream.bitstream} {bitstream.vfiles}")
                    transaction_log.info(f"add_enum_sample error {e}")
                    raise


        return fuzzloops.chain(futures, f"Enum Setting {config.device}", integrate_bitstreams )

def fuzz_ip_word_setting(config, name, length, get_sv_substs, desc="", default=None, overlay="", executor = None):
    """
    Fuzz a multi-bit IP setting with an optimum number of bitstreams

    :param config: FuzzConfig instance containing target device and tile of interest
    :param name: name of the setting to store in the database
    :param length: number of bits in the setting
    :param get_sv_substs: a callback function, that is called with an array of bits to create a design with that setting
    """
    if not fuzzconfig.should_fuzz_platform(config.device):
        return

    if config.check_deltas(name):
        return

    prefix = f"{name}/"

    inverted_mode = False
    if default is not None:
        for i in range(0, length.bit_length()):
            bits = [(j >> i) & 0x1 == 0 for j in range(length)]
            if default == bits:
                inverted_mode = True
                break

    with fuzzloops.Executor(executor) as executor:
        baseline_future = config.build_design_future(executor, config.sv, get_sv_substs([inverted_mode for _ in range(length)]), prefix)

        bitstream_futures = [
            config.build_design_future(executor, config.sv, get_sv_substs([(j >> i) & 0x1 == (1 if inverted_mode else 0) for j in range(length)]), f"{prefix}/{i}/")
            for i in range(0, length.bit_length())
        ]

        def integrate_bitstreams(bitstreams):
            baseline = bitstreams[0]
            ipcore, iptype = config.tiles[0].split(":")
            with fuzzconfig.db_lock() as db:
                fz = libpyprjoxide.IPFuzzer.word_fuzzer(db, baseline.bitstream, ipcore, iptype, name, desc, length, inverted_mode, overlay=overlay)
                for (i, bitfile) in enumerate(bitstreams[1:]):
                    bits = [(j >> i) & 0x1 == (1 if inverted_mode else 0) for j in range(length)]
                    fz.add_word_sample(db, bits, bitfile.bitstream)
                config.solve(fz, db)

        return fuzzloops.chain([baseline_future, *bitstream_futures], f"IP Word {config.device}", integrate_bitstreams)

def fuzz_ip_enum_setting(config, empty_bitfile, name, values, get_sv_substs, desc="", overlay="",executor = None):
    """
    Fuzz a multi-bit IP enum with an optimum number of bitstreams

    :param config: FuzzConfig instance containing target device and tile of interest
    :param empty_bitfile: a baseline empty bitstream to diff against
    :param name: name of the setting to store in the database
    :param values: list of values taken by the enum
    :param get_sv_substs: a callback function, 
    """
    if not fuzzconfig.should_fuzz_platform(config.device):
        return

    if config.check_deltas(name):
        return

    ipcore, iptype = config.tiles[0].split(":")
    prefix = f"{ipcore}/{name}"

    with fuzzloops.Executor(executor) as executor:
        bitstream_futures = [
            config.build_design_future(executor, config.sv, get_sv_substs(opt), f"{prefix}/{opt}/")
            for opt in values
        ]

        def integrate_bitstreams(bitstreams):
            with fuzzconfig.db_lock() as db:
                fz = libpyprjoxide.IPFuzzer.enum_fuzzer(db, empty_bitfile.bitstream, ipcore, iptype, name, desc, overlay=overlay)
                for (opt, bitfile) in zip(values, bitstreams):
                    fz.add_enum_sample(db, opt, bitfile.bitstream)
                config.solve(fz, db)

        return fuzzloops.chain(bitstream_futures,  f"IP Enum {config.device}", integrate_bitstreams)

def fuzz_primitive_definition(cfg, empty, site, primitive, mark_relative_to = None, mode_name = None, get_substs=None):
    def default_get_substs(mode="NONE", kv=None):
        if kv is None:
            config = ""
        else:
            key = kv[0]
            if key.endswith("MUX"):
                key = ":" + key[:-3]
            config = f"{mode}:::{key}={kv[1]}"
        return dict(cmt="//" if mode == "NONE" else "",
                    config=config,
                    site=site)
    if get_substs is None:
        get_substs = default_get_substs

    if mode_name is None:
        mode_name = primitive.mode

    for setting in primitive.settings:
        subs_fn = lambda x, name=setting.name: get_substs(mode=mode_name, kv=(name, x))
        if setting.name == "MODE":
            subs_fn = lambda x: get_substs(mode=x)

        if isinstance(setting, EnumSetting):
            fuzz_enum_setting(cfg, empty, f"{mode_name}.{setting.name}", setting.values, subs_fn,False,
            desc=setting.desc, mark_relative_to=mark_relative_to)


