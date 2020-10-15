# Project Oxide - documenting Lattice's 28nm "Nexus" FPGA parts

## Current Status

A framework is in place to parse bitstreams and fuzz bitstream changes. Currently the logic tile (PLC) config and interconnect; basic IO and IOLOGIC config; EBR config; global routing and basic DSP config have been fuzzed. Remaining work includes finishing IO and DSP fuzzing; and fuzzing the hard IP like PCIe, PLLs and DPHY.

nextpnr development is currently in [this branch](https://github.com/daveshah1/nextpnr/tree/nextpnr-nexus).

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

## Building the end user tool

A single command line tool `prjoxide` supports subcommands for bitstream packing and unpacking as well as BBA generation for the nextpnr build process. To build and install it, run:

    cd libprjoxide
    cargo install --path prjoxide

This will, by default, install to `~/.cargo/bin` which you may need to add to your `PATH`. You can use `--root` or the `CARGO_INSTALL_ROOT` environment variable to override the installation root.

This executable contains all data embedded in it; so it can be freely moved to another location on your system if required. Consequently, however, you will need to rebuild prjoxide after a database update.
