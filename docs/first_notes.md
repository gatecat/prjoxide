# First LIFCL-40 notes
 - preamble, and first commands same as ECP5
 - IDCODE 0x010f1043
 - Seems to use frame addresses to write frames out of order,
   first writes some frames at 0x8000, rather than all at once like ECP5?
 - new 0x56 command - "Power Control Frame" according to programming file utility
 - 16-bit frame CRC is BUYPASS, same as ECP5
 - Documentation mentions "14 parity bits" per frame. These seem to be before 16-bit frame CRC. Unsure if actually checked or not
 - Hard IP like PCIe configured outside of main bitstream
    `F6 000000 address` writes a 32-bit address
    `72 D00001 data CRC` writes a 32-bit data word with 16-bit CRC
