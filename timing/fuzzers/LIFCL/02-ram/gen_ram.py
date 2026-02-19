import random

print("module top(input [3:0] clk, ce, rst, input [7:0] d, output [7:0] q);")
data = ["d[{}]".format(i) for i in range(8)]

def data_bits(N):
    return "{{{}}}".format(", ".join([random.choice(data) for i in range(N)]))
def clock_port(name):
    print("        .{}(clk[{}]),".format(name, random.randint(0, 3)))
def ce_port(name):
    print("        .{}(ce[{}]),".format(name, random.randint(0, 3)))
def rst_port(name):
    print("        .{}(rst[{}]),".format(name, random.randint(0, 3)))
def data_port(name, N):
    print("        .{}({}),".format(name, data_bits(N)))
def output_port(name, i, j, N, last=False):
    print("        .{}(d_{}[{} +: {}]){}".format(name, i, j, N, "" if last else ","))

def get_next_data(i, N):
    print("    wire [{}:0] d_{};".format(N-1, i))
    return ["d_{}[{}]".format(i, j) for j in range(N)]

N = 80

for i in range(N):
    prim = random.choice(["DP16K", "PDP16K", "PDPSC16K", "SP16K", "FIFO16K"])
    if prim == "DP16K":
        next_data = get_next_data(i, 18+18)
        print("    DP16K ram_{} (".format(i))
        clock_port("CLKA")
        clock_port("CLKB")
        ce_port("CEA")
        ce_port("CEB")
        ce_port("WEA")
        ce_port("WEB")
        rst_port("RSTA")
        rst_port("RSTB")
        data_port("CSA", 3)
        data_port("CSB", 3)
        data_port("ADA", 14)
        data_port("ADB", 14)
        data_port("DIA", 18)
        data_port("DIB", 18)
        output_port("DOA", i, 0,  18, False)
        output_port("DOB", i, 18, 18, True)
        print("    );")
    elif prim == "PDP16K":
        next_data = get_next_data(i, 36+2)
        print("    PDP16K ram_{} (".format(i))
        clock_port("CLKW")
        clock_port("CLKR")
        ce_port("CEW")
        ce_port("CER")
        rst_port("RST")
        data_port("CSW", 3)
        data_port("CSR", 3)
        data_port("ADW", 14)
        data_port("ADR", 14)
        data_port("DI", 36)
        output_port("DO", i, 0,  36, False)
        output_port("ONEBITERR", i, 36,  1, False)
        output_port("TWOBITERR", i, 37,  1, True)
        print("    );")
    elif prim == "PDPSC16K":
        next_data = get_next_data(i, 36+2)
        print("    PDPSC16K ram_{} (".format(i))
        clock_port("CLK")
        ce_port("CEW")
        ce_port("CER")
        rst_port("RST")
        data_port("CSW", 3)
        data_port("CSR", 3)
        data_port("ADW", 14)
        data_port("ADR", 14)
        data_port("DI", 36)
        output_port("DO", i, 0,  36, False)
        output_port("ONEBITERR", i, 36,  1, False)
        output_port("TWOBITERR", i, 37,  1, True)
        print("    );")
    elif prim == "SP16K":
        next_data = get_next_data(i, 18)
        print("    SP16K ram_{} (".format(i))
        clock_port("CLK")
        ce_port("CE")
        ce_port("WE")
        rst_port("RST")
        data_port("CS", 3)
        data_port("AD", 14)
        data_port("DI", 18)
        output_port("DO", i, 0,  18, True)
        print("    );")
    elif prim == "FIFO16K":
        next_data = get_next_data(i, 18+18+6)
        print("    FIFO16K ram_{} (".format(i))
        clock_port("CLKW")
        clock_port("CLKR")
        ce_port("WE")
        ce_port("RE")
        # ce_port("WEA")
        # ce_port("WEB")
        rst_port("RSTW")
        rst_port("RPRST")
        data_port("FULLI", 1)
        data_port("EMPTYI", 1)
        data_port("CSW", 2)
        data_port("CSR", 2)
        data_port("DI", 36)
        output_port("DO", i, 0, 36, False)
        output_port("ONEBITERR", i, 36,  1, False)
        output_port("TWOBITERR", i, 37,  1, False)
        output_port("ALMOSTFULL", i, 38,  1, False)
        output_port("FULL", i, 39,  1, False)
        output_port("ALMOSTEMPTY", i, 40,  1, False)
        output_port("EMPTY", i, 41,  1, True)
        print("    );")
    else:
        assert False
    data = next_data

print("    assign q = {};".format(data_bits(8)))
print("endmodule")
