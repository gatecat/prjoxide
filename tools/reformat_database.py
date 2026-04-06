import database
import sys
import fuzzconfig
import tiles

def main():
    devices = database.get_devices()

    for family in sorted(devices["families"].keys()):
        for device in sorted(devices["families"][family]["devices"].keys()):

            with fuzzconfig.db_lock() as db:
                for tiletype in tiles.get_tiletypes(device):
                    db.load_tiletype(family, tiletype)
                db.reformat()


if __name__ == "__main__":
    main()

