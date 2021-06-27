# Project Oxide - documenting Lattice's 28nm "Nexus" FPGA parts

## Current Status

A framework is in place to parse bitstreams and fuzz bitstream changes. Currently the logic tile (PLC) config and interconnect; basic IO and IOLOGIC config; EBR config; global routing ; DSP and PLL config have been fuzzed. Remaining work includes finishing IO, PCIe and SGMII fuzzing.

prjoxide may also need to be updated to support the production silicon. Most of the current testing has been done with LIFCL-40 devices, with limited testing on the LIFCL-17. There has also been some early investigations into Certus-Pro NX support.

prjoxide is also aiming to support the [SymbiFlow FPGA interchange format](https://github.com/SymbiFlow/fpga-interchange-schema) and includes support for generating (currently incomplete) device resource data. This is not yet a working end to end flow and currently the direct nextpnr based flow described below should be used.

## Links

- [HTML documentation](https://gatecat.github.io/prjoxide-html/)

## Getting Started - Complete Flow

### Prerequisites

 - Install the nextpnr and Yosys prerequisites (example for Ubuntu):
 ```
    sudo apt-get install build-essential clang bison flex libreadline-dev \
                     gawk tcl-dev libffi-dev git mercurial graphviz   \
                     xdot pkg-config python python3 libftdi-dev \
                     qt5-default python3-dev libboost-all-dev cmake libeigen3-dev
```
 - Build and install latest git [Yosys](https://github.com/YosysHQ/yosys)
 - Install a Rust toolchain using [rustup](https://rustup.rs/)
 - Build and install [ecpprog](https://github.com/gregdavill/ecpprog)

### Building the prjoxide tool

Clone prjoxide recursively, so you get a copy of the database too:

    git clone --recursive https://github.com/gatecat/prjoxide

A single command line tool `prjoxide` supports subcommands for bitstream packing and unpacking as well as BBA generation for the nextpnr build process. To build and install it, run:

    cd libprjoxide
    cargo install --path prjoxide

This will, by default, install to `~/.cargo/bin` which you may need to add to your `PATH`. You can use `--root` or the `CARGO_INSTALL_ROOT` environment variable to override the installation root.

This executable contains all data embedded in it; so it can be freely moved to another location on your system if required. Consequently, however, you will need to rebuild prjoxide after a database update.

### Building nextpnr-nexus

Clone nextpnr:

    git clone --recursive https://github.com/YosysHQ/nextpnr
    cd nextpnr

Build nextpnr-nexus, making sure to point it to the correct path for the prjoxide tool:

    cmake -DARCH=nexus -DOXIDE_INSTALL_PREFIX=$HOME/.cargo .
    make -j8

### Running the example designs

There are currently examples for the CrossLink-NX EVN and VIP boards in prjoxide.

    cd prjoxide/examples/blinky_evn
    make prog

For more advanced test designs; [LiteX](https://github.com/enjoy-digital/litex) supports the CrossLink-NX device using prjoxide. For example:

    python litex-boards/litex_boards/targets/crosslink_nx_vip.py --toolchain oxide --nexus-es-device --build

## Getting Started - Developers

The main framework (libprjoxide) is written in Rust. As the development side includes Python bindings using pyo3 for fuzzers and miscellaneous utilities, nightly Rust will be required. It is strongly recommended to use [rustup](https://rustup.rs/) to install this.

Once installed, run the following to build libprjoxide:

    cd libprjoxide
    cargo build --release

To run the Python scripts, add all of the needed libraries to `PYTHONPATH` using:

    source environment.sh

If running fuzzers, you might also need to adjust the path to Radiant in `user_environment.sh` (which will be created by the above script).
