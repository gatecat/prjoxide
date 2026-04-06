# Bitstream Format

The format of the bitstream has many similarities to ECP5 and previous Lattice devices. It is still a command-based format with many similar commands, albeit with changes for some of the new features.

## "Magic" and comments

The first four bytes of the bitstream are `0x4C 0x53 0x43 0x43` (**LSCC**, i.e. Lattice SemiConductor Corporation). *(TODO: test - this may be needed for SPI flash boot to work.)*

This the follows an option comment section, which is bounded by `0xFF 0x00` and `0x00 0xFF`. It contains several null-terminated strings used by tools like Radiant Programmer to determine the device, package, build date/time etc. It is not parsed by the chip.

## Preamble

The four bytes marking the start of an actual bitstream are `0xFF 0xFF 0xBD 0xB3`, the same as the ECP5.

## Commands

All commands (except the `0xFF` dummy command) are followed by three "parameter" bytes and then zero or more bytes of payload. All multi-byte integers are big endian.

 - **LSC_RESET_CRC** (`0x3B`): resets the internal CRC16 counter
 - **VERIFY_ID** (`0xE2`): after th 3 param bytes; followed by the 32-bit device IDCODE. Config ends if IDCODE does not match
 - **LSC_PROG_CNTRL0** (`0x22`): sets the value of control register 0, which contains various settings such as config clock frequency and multiboot mode
 - **LSC_INIT_ADDRESS** (`0x46`): sets the frame address counter to 0
 - **LSC_WRITE_ADDRESS** (`0xB4`): sets the frame address counter to the 32-bit payload
 - **LSC_PROG_INCR_RTI** (`0x82`): programs configuration frames at incrementing addresses. First param byte contains general settings and next two contain 16-bit frame count. See **Config Frames** section for more info
 - **ISC_PROGRAM_USERCODE** (`0xC2`): sets the usercode to the 32-bit payload
 - **LSC_BUS_ADDRESS** (`0xF6`): sets the IP/RAM bus address to the 32-bit payload
 - **LSC_BUS_WRITE** (`0x72`): writes to the IP/RAM bus at incrementing addresses. First param byte contains general settings and next two contain 16-bit word count
 - **ISC_PROGRAM_DONE** (`0x5E`): ends configuration and starts FPGA fabric running
 - **LSC_POWER_CTRL** (`0x56`): third param byte configures internal power switches (detail unknown)

Fuller table available [here](https://www.latticesemi.com/-/media/LatticeSemi/Documents/ApplicationNotes/PT3/FPGA-TN-02099-3-5-sysCONFIG-User-Guide-for-Nexus-Platform.ashx?document_id=52790). 

## Config Frames

Configuration bits are two dimensional. For a given device, there is a grid of frame_cnt by bits_per_frame size. Each tile configuration exists as a sub rectangle inside of the overall device grid. Each tile in the tilegrid.json file specifies the coordinates for that tiles configuration data.

An important detail is that the relative bits in each tile sharing a tiletype mean the same thing for that tile. This means that when we have the configuration mapping for a single tile, we have it for all tiles of that type as well. 

Config frames are written in three chunks (numbers for LIFCL):

 - 32 frames at address 0x8000 set up left and right side IO/IP
 - 9116 at address 0x0000 set up general fabric (the vast majority of the device)
 - 24 frames at address 0x8020 set up global clocking "tap"s

It is believed this ordering is for the "early IO release" feature.

The final 14 bits of each config frame are used for an error correcting code ("parity").
This uses the typical CRC algorithm with polynomial 0x202D.

The error correcting code does not include LUT RAM initialisation bits,
these are masked with zeroes, because they can change at runtime.

Following each frame is the standard packet CRC16, which uses the common 0x8005 polynomial.

## IP/RAM bus

IP and RAM configuration and initialisation is not done using general configuration frames but using a special bus, which for IP mirrors the LMMI bus exposed to fabric.

The first byte of the 32-bit bus address is used to determine the destination type, and the word size for **LSC_BUS_WRITE**:

 - **0x0** is for non-PCIe IP cores (PLL, DPHY, etc) config. Words are 8 bits.
 - **0x2** is for BRAM and LRAM initialisation. Words are 40 bits.
 - **0x3** is for PCIe IP config. Words are 32 bits



