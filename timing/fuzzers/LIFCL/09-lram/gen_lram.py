import argparse
import random
import json

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--vlog",
        type=str,
        required=True,
        help="Output Verilog file"
    )
    parser.add_argument(
        "--conf",
        type=str,
        required=True,
        help="Output cell configuration file"
    )

    args = parser.parse_args()

    vlog = open(args.vlog, "w")

    print("module top(input [3:0] clk, ce, rst, input [7:0] d, output [7:0] q);", file=vlog)
    data = ["d[{}]".format(i) for i in range(8)]

    def data_bits(N):
        return "{{{}}}".format(", ".join([random.choice(data) for i in range(N)]))
    def clock_port(name):
        print("        .{}(clk[{}]),".format(name, random.randint(0, 3)), file=vlog)
    def ce_port(name):
        print("        .{}(ce[{}]),".format(name, random.randint(0, 3)), file=vlog)
    def rst_port(name):
        print("        .{}(rst[{}]),".format(name, random.randint(0, 3)), file=vlog)
    def data_port(name, N):
        print("        .{}({}),".format(name, data_bits(N)), file=vlog)
    def output_port(name, i, j, N, last=False):
        print("        .{}(d_{}[{} +: {}]){}".format(name, i, j, N, "" if last else ","), file=vlog)

    def get_next_data(i, N):
        print("    wire [{}:0] d_{};".format(N-1, i), file=vlog)
        return ["d_{}[{}]".format(i, j) for j in range(N)]

    N = 5
    config = {}

    for i in range(N):
        lram_prim = random.choice(["DPSC512K", "PDPSC512K", "SP512K"])
        if lram_prim == "DPSC512K":
            oreg_a = random.choice(["NO_REG", "OUT_REG"])
            oreg_b = random.choice(["NO_REG", "OUT_REG"])
            next_data = get_next_data(i, 32+32+4)
            print("    DPSC512K #(.OUTREG_A(\"{}\"),.OUTREG_B(\"{}\")) lram_{} (".format(oreg_a, oreg_b, i), file=vlog)
            clock_port("CLK")
            ce_port("CEA")
            ce_port("CEB")
            ce_port("WEA")
            ce_port("WEB")
            ce_port("CSA")
            ce_port("CSB")
            ce_port("CEOUTA")
            ce_port("CEOUTB")
            rst_port("RSTA")
            rst_port("RSTB")
            data_port("BENA_N", 4)
            data_port("BENB_N", 4)
            data_port("ADA", 14)
            data_port("ADB", 14)
            data_port("DIA", 32)
            data_port("DIB", 32)
            output_port("DOA", i, 0,  32, False)
            output_port("DOB", i, 32, 32, False)
            output_port("ERRDECA", i, 64, 2, False)
            output_port("ERRDECB", i, 66, 2, True)
            print("    );", file=vlog)

            key = f"lram_{i}"
            config[key] = {
                "type": "DPC512K",
                "params": {
                    "OUTREG_A": oreg_a,
                    "OUTREG_B": oreg_b,
                },
            }

        elif lram_prim == "PDPSC512K":
            oreg = random.choice(["NO_REG", "OUT_REG"])
            next_data = get_next_data(i, 32+4)
            print("    PDPSC512K #(.OUTREG(\"{}\")) lram_{} (".format(oreg, i), file=vlog)
            clock_port("CLK")
            ce_port("CEW")
            ce_port("CER")
            ce_port("WE")
            ce_port("CSW")
            ce_port("CSR")
            rst_port("RSTR")
            data_port("BYTEEN_N", 4)
            data_port("ADW", 14)
            data_port("ADR", 14)
            data_port("DI", 32)
            output_port("DO", i, 0,  32, False)
            output_port("ERRDECA", i, 32, 2, False)
            output_port("ERRDECB", i, 34, 2, True)
            print("    );", file=vlog)

            key = f"lram_{i}"
            config[key] = {
                "type": "PDPSC512K",
                "params": {
                    "OUTREG": oreg,
                },
            }

        elif lram_prim == "SP512K":
            oreg = random.choice(["NO_REG", "OUT_REG"])
            next_data = get_next_data(i, 32+4)
            print("    SP512K #(.OUTREG(\"{}\")) lram_{} (".format(oreg, i), file=vlog)
            clock_port("CLK")
            ce_port("CE")
            ce_port("WE")
            ce_port("CS")
            ce_port("CEOUT")
            rst_port("RSTOUT")
            data_port("BYTEEN_N", 4)
            data_port("AD", 14)
            data_port("DI", 32)
            output_port("DO", i, 0,  32, False)
            output_port("ERRDECA", i, 32, 2, False)
            output_port("ERRDECB", i, 34, 2, True)
            print("    );", file=vlog)

            key = f"lram_{i}"
            config[key] = {
                "type": "SP512K",
                "params": {
                    "OUTREG": oreg,
                },
            }

        else:
            assert False
        data = next_data
    print("    assign q = {};".format(data_bits(8)), file=vlog)
    print("endmodule", file=vlog)

    with open(args.conf, "w") as fp:
        fp.write(json.dumps(config, sort_keys=True, indent=2))

if __name__ == "__main__":
    main()
