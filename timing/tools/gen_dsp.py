import numpy as np

# (name, cost, a_width, b_with, c_width, z_width, extra_registers)
prims = [
    ("MULT18X18",       2,  18,     18,   None,   36, ()),
    ("MULT18X36",       4,  18,     36,   None,   54, ()),
    ("MULT36X36",       8,  36,     36,   None,   72, ()),
    ("MULT9X9",         1,   9,      9,   None,   18, ()),
    ("MULTADDSUB18X18", 4,  18,     18,     54,   54, ("ADDSUB", "CIN")),
    ("MULTADDSUB18X36", 4,  18,     36,     54,   54, ("ADDSUB", "CIN")),
    ("MULTADDSUB36X36", 8,  36,     36,    108,  108, ("ADDSUB", "CIN")),
    ("MULTPREADD18X18", 2,  18,     18,     18,   36, ()),
    ("MULTPREADD9X9",   1,   9,      9,      9,   18, ()),
]

max_cost = 56

print("module top(input clk, input [3:0] ce, input [3:0] rst, input [7:0] d, output [7:0] q);")
data = ["d[{}]".format(i) for i in range(8)]
curr_cost = 0
i = 0

while True:
    prim, cost, A, B, C, Z, regs = prims[np.random.randint(len(prims))]
    curr_cost += cost
    if curr_cost > max_cost:
        break
    a = "{{{}}}".format(", ".join(np.random.choice(data) for j in range(A)))
    b = "{{{}}}".format(", ".join(np.random.choice(data) for j in range(B)))
    if C is not None:
        c = "{{{}}}".format(", ".join(np.random.choice(data) for j in range(C)))
    print("    wire [{}:0] d_{};".format(Z-1, i))
    print("    {} #(".format(prim))
    print("        .REGINPUTA(\"{}\"),".format(np.random.choice(["REGISTER", "BYPASS"])))
    print("        .REGINPUTB(\"{}\"),".format(np.random.choice(["REGISTER", "BYPASS"])))
    if C is not None:
        print("        .REGINPUTC(\"{}\"),".format(np.random.choice(["REGISTER", "BYPASS"])))
    for er in regs:
         print("        .REG{}(\"{}\"),".format(er, np.random.choice(["REGISTER", "BYPASS"])))
    print("        .REGOUTPUT(\"{}\"),".format(np.random.choice(["REGISTER", "BYPASS"])))
    print("        .RESETMODE(\"{}\")".format(np.random.choice(["SYNC", "ASYNC"])))
    print("   ) dsp_{} (".format(i))
    print("       .A({}),".format(a))
    print("       .B({}),".format(b))
    if C is not None:
        print("       .C({}),".format(c))
    print("       .CLK(clk),")
    print("       .CEA(ce[{}]),".format(np.random.randint(4)))
    print("       .CEB(ce[{}]),".format(np.random.randint(4)))
    print("       .RSTA(rst[{}]),".format(np.random.randint(4)))
    print("       .RSTB(rst[{}]),".format(np.random.randint(4)))
    print("       .Z(d_{})".format(i))
    print("   );")
    data =  ["d_{}[{}]".format(i, j) for j in range(Z)]
    i += 1

print("    assign q = {{{}}};".format(", ".join(np.random.choice(data) for j in range(8))))
print("endmodule")
