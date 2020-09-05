import database
import libprjoxide

def main():
    db = libprjoxide.Database(database.get_db_root())
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B5_1", ["SYSIO_B5_1_V18"], "PEWC", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B4_0", ["SYSIO_B4_0_DQS1", "SYSIO_B4_0_DQS3", "SYSIO_B4_0_DLY50", "SYSIO_B4_0_DLY42"], "PEWC", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B4_1", ["SYSIO_B4_1_DQS0", "SYSIO_B4_1_DQS2", "SYSIO_B4_1_DQS4", "SYSIO_B4_1_DLY52"], "PEWC", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B3_0", ["SYSIO_B3_0_DLY30_V18", "SYSIO_B3_0_DQS1", "SYSIO_B3_0_DQS3"], "PEWC", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B3_1", ["SYSIO_B3_1_DLY32", "SYSIO_B3_1_DQS0", "SYSIO_B3_1_DQS2", "SYSIO_B3_1_DQS4", "SYSIO_B3_1_ECLK_R", "SYSIO_B3_1_V18"], "PEWC", "")

    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B1_0_ODD", ["SYSIO_B1_0_C"], "C", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B2_0_ODD", ["SYSIO_B2_0_C"], "C", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B6_0_ODD", ["SYSIO_B6_0_C"], "C", "")
    libprjoxide.copy_db(db, "LIFCL", "SYSIO_B7_0_ODD", ["SYSIO_B7_0_C"], "C", "")

if __name__ == '__main__':
    main()
