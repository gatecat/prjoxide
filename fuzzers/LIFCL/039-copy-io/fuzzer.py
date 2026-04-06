import database
import libpyprjoxide
import database

def main():

    lilfcl_tile_types = database.get_tiletypes("LIFCL")
    def get_tiletypes_with_prefix(prefix):
        return [k for k in lilfcl_tile_types if k.startswith(prefix)]

    db = libpyprjoxide.Database(database.get_db_root())
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B5_1", ["SYSIO_B5_1_V18", "SYSIO_B5_1_15K_DQS51", "SYSIO_B5_1_15K_DQS50", "SYSIO_B5_1_15K_ECLK_L_V52"], "PEWC", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B5_0", ["SYSIO_B5_0_15K_DQS52"], "PEWC", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B4_0", ["SYSIO_B4_0_DQS1", "SYSIO_B4_0_DQS3", "SYSIO_B4_0_DLY50", "SYSIO_B4_0_DLY42", "SYSIO_B4_0_15K_DQS42", "SYSIO_B4_0_15K_BK4_V42", "SYSIO_B4_0_15K_V31"], "PEWC", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B4_1", ["SYSIO_B4_1_DQS0", "SYSIO_B4_1_DQS2", "SYSIO_B4_1_DQS4", "SYSIO_B4_1_DLY52", "SYSIO_B4_1_15K_DQS41"], "PEWC", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B3_0", get_tiletypes_with_prefix("SYSIO_B3_0_"), "PEWC", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B3_1", get_tiletypes_with_prefix("SYSIO_B3_1_"), "PEWC", "")

    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B1_0_ODD", ["SYSIO_B1_0_C"], "C", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B2_0_ODD", ["SYSIO_B2_0_C"], "C", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B6_0_ODD", ["SYSIO_B6_0_C"], "C", "")
    libpyprjoxide.copy_db(db, "LIFCL", "SYSIO_B7_0_ODD", ["SYSIO_B7_0_C"], "C", "")

if __name__ == '__main__':
    main()
