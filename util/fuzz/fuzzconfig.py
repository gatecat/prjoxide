"""
This module provides a structure to define the fuzz environment
"""
import os
from os import path
from string import Template
import radiant
import database
import libpyprjoxide

db = None

class FuzzConfig:
    def __init__(self, device, job, tiles, sv):
        """
        :param job: user-friendly job name, used for folder naming etc
        :param device: Target device name
        :param tiles: List of tiles to consider during fuzzing
        :param sv: Minimal structural Verilog file to use as a base for interconnect fuzzing
        """
        self.device = device
        self.job = job
        self.tiles = tiles
        self.sv = sv
        self.rbk_mode = True if self.device == "LFCPNX-100" else False
        self.struct_mode = True
        self.udb_specimen = None

    @property
    def workdir(self):
        return path.join(".", "work", self.job)

    def make_workdir(self):
        """Create the working directory for this job, if it doesn't exist already"""
        os.makedirs(self.workdir, exist_ok=True)

    def setup(self, skip_specimen=False):
        """
        Create a working directory, and run Radiant on a minimal Verilog file to create a udb for Tcl usage etc
        """

        # Load the global database if it doesn't exist already
        global db
        if db is None:
            db = libpyprjoxide.Database(database.get_db_root())

        self.make_workdir()
        if not skip_specimen:
            self.build_design(self.sv, {})

    def build_design(self, des_template, substitutions, prefix="", substitute=True):
        """
        Run Radiant on a given design template, applying a map of substitutions, plus some standard substitutions
        if not overriden.

        :param des_template: path to template (structural) Verilog file
        :param substitutions: dictionary containing template subsitutions to apply to Verilog file
        :param prefix: prefix to append to filename, for running concurrent jobs without collisions

        Returns the path to the output bitstream
        """
        subst = dict(substitutions)
        if "arcs_attr" not in subst:
            subst["arcs_attr"] = ""
        if "device" not in subst:
            subst["device"] = self.device
        desfile = path.join(self.workdir, prefix + "design.v")
        bitfile = path.join(self.workdir, prefix + "design.bit")

        if "sysconfig" in subst:
            pdcfile = path.join(self.workdir, prefix + "design.pdc")
            with open(pdcfile, "w") as pdcf:
                pdcf.write("ldc_set_sysconfig {{{}}}\n".format(subst["sysconfig"]))

        if path.exists(bitfile):
            os.remove(bitfile)
        with open(des_template, "r") as inf:
            with open(desfile, "w") as ouf:
                if substitute:
                    ouf.write(Template(inf.read()).substitute(**subst))
                else:
                    ouf.write(inf.read())
        radiant.run(self.device, desfile, struct_ver=self.struct_mode, raw_bit=False, rbk_mode=self.rbk_mode)
        if self.struct_mode and self.udb_specimen is None:
            self.udb_specimen = path.join(self.workdir, prefix + "design.tmp", "par.udb")
        return bitfile


    @property
    def udb(self):
        """
        A udb file specimen for Tcl
        """
        assert self.udb_specimen is not None
        return self.udb_specimen
