# First LIFCL-40 notes
 - preamble, and first commands same as ECP5
 - IDCODE 0x010f1043
 - Seems to use frame addresses to write frames out of order,
   first writes some frames at 0x8000, rather than all at once like ECP5?
 - new 0x56 command - "Power Control Frame" according to programming file utility
