
#!/usr/bin/env python3
"""
For each family and device, obtain a tilegrid and save it in the database
"""

import os
from os import path
import subprocess
import extract_tilegrid

import database

def main():
    devices = database.get_devices()
    for family in sorted(devices["families"].keys()):
        for device in sorted(devices["families"][family]["devices"].keys()):
            output_file = path.join(database.get_db_subdir(family, device), "tilegrid.json")
            subprocess.check_call(["./get_device_tilegrid.sh", device])
            extract_tilegrid.main(["extract_tilegrid", device, "../minitests/simple/wire.dump", output_file])


if __name__ == "__main__":
    main()
