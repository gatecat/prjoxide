#!/bin/bash

# Script to run a single Radiant command
# You need to set the RADIANTDIR environment variable to the path where you have
# installed Lattice Radiant, unless it matches this default.

radiantdir="${RADIANTDIR:-$HOME/lscc/radiant/3.0}"
export FOUNDRY="${radiantdir}/ispfpga"
bindir="${radiantdir}/bin/lin64"
LSC_DIAMOND=true
export LSC_DIAMOND
export NEOCAD_MAXLINEWIDTH=32767
export TCL_LIBRARY="${radiantdir}/tcltk/linux/lib/tcl8.6"
export fpgabindir=${FOUNDRY}/bin/lin64
export LD_LIBRARY_PATH="${bindir}:${fpgabindir}"
export LM_LICENSE_FILE="${radiantdir}/license/license.dat"
export LSC_SHOW_INTERNAL_ERROR=1
PATH=$FOUNDRY/bin/lin64:$bindir:$PATH exec $*
