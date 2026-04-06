import sys
import os
import logging
import libpyprjoxide

def main():
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logging.basicConfig(
        level=LOGLEVEL,
    )

    frm_db_path = sys.argv[1]
    to_db_path = sys.argv[2]

    frm_db = libpyprjoxide.Database(frm_db_path)
    to_db = libpyprjoxide.Database(to_db_path)

    to_db.merge(frm_db)
    to_db.flush()

if __name__ == "__main__":
    main()
