# Project Oxide - documenting Lattice's 28nm "Nexus" FPGA parts

## Current Status

A framework is in place to parse bitstreams and fuzz bitstream changes. Currently the logic tile (PLC) config and interconnect; basic IO and IOLOGIC config; one set of EBR config; global routing and basic DSP config have been fuzzed. Remaining work includes non-logic interconnect (CIB) fuzzing; finishing EBR, IO and DSP fuzzing; and fuzzing the hard IP like PCIe, PLLs and DPHY.

No work has yet begun on the nextpnr or bitstream generation side.

## Links

- [HTML documentation](https://daveshah1.github.io/prjoxide-html/)

## Getting Started - Developers

The main framework (libprjoxide) is written in Rust. As the development side includes Python bindings using pyo3 for fuzzers and miscellaneous utilities, nightly Rust will be required. It is strongly recommended to use [rustup](https://rustup.rs/) to install this.

Once installed, run the following to build libprjoxide:

    cd libprjoxide
    cargo build --release

To run the Python scripts, add all of the needed libraries to `PYTHONPATH` using:

    source environment.sh

If running fuzzers, you might also need to adjust the path to Radiant in `user_environment.sh` (which will be created by the above script).
