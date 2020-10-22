import database
import libpyprjoxide

def main():
    db = libpyprjoxide.Database(database.get_db_root())
    libpyprjoxide.copy_db(db, "LIFCL", "EBR_10", ["TRUNK_L_EBR_10", ], "PEWC", "")

if __name__ == '__main__':
    main()
