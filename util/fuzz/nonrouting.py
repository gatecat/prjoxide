"""
Utilities for fuzzing non-routing configuration. This is the counterpart to interconnect.py
"""

import threading
import tiles
import libprjoxide
import fuzzconfig

def fuzz_word_setting(config, name, length, get_sv_substs):
    """
    Fuzz a multi-bit setting, such as LUT initialisation

    :param config: FuzzConfig instance containing target device and tile of interest
    :param name: name of the setting to store in the database
    :param length: number of bits in the setting
    :param get_sv_substs: a callback function, that is called with an array of bits to create a design with that setting
    """
    prefix = "thread{}_".format(threading.get_ident())
    baseline = config.build_design(config.sv, get_sv_substs([False for _ in range(length)]), prefix)
    fz = libprjoxide.Fuzzer.word_fuzzer(fuzzconfig.db, baseline, set(config.tiles), name, length, baseline)
    for i in range(length):
        i_bit = config.build_design(config.sv, get_sv_substs([(_ == i) for _ in range(length)]), prefix)
        fz.add_word_sample(fuzzconfig.db, i, i_bit)
    fz.solve(fuzzconfig.db)

def fuzz_enum_setting(config, empty_bitfile, name, values, get_sv_substs, include_zeros=True):
    """
    Fuzz a setting with multiple possible values

    :param config: FuzzConfig instance containing target device and tile of interest
    :param empty_bitfile: a baseline empty bitstream to diff against
    :param name: name of the setting to store in the database
    :param values: list of values taken by the enum
    :param get_sv_substs: a callback function, 
    :param include_zeros: if set, bits set to zero are not included in db. Needed for settings such as CEMUX which share
    bits with routing muxes to prevent conflicts.
    """
    prefix = "thread{}_".format(threading.get_ident())
    fz = libprjoxide.Fuzzer.enum_fuzzer(fuzzconfig.db, empty_bitfile, set(config.tiles), name, include_zeros)
    for opt in values:
        opt_bit = i_bit = config.build_design(config.sv, get_sv_substs(opt), prefix)
        fz.add_enum_sample(fuzzconfig.db, opt, opt_bit)
    fz.solve(fuzzconfig.db)

