dffs = []

for clk in ("clk", "clkn"):
    for lsr in ("lsr", "lsrn", "1'b0"):
        for ce in ("ce", "cen", "1'b0"):
            for d in ("d", "x ^ d"):
                for prim, sr in [("FD1P3BX", "PD"), ("FD1P3DX", "CD"), ("FD1P3IX", "CD"), ("FD1P3JX", "PD")]:
                    i = len(dffs)
                    dffs.append("{prim} LOGIC_DFF_{i} (.D({d}[{i}]), .CK({ck}), .SP({ce}), .{sr}({lsr}), .Q(q[{i}]));".format(
                            prim=prim, i=i, d=d, ck=clk, ce=ce, sr=sr, lsr=lsr,
                        ))

print("module top(input clk, lsr, ce, x, input [{0}:0] d, input [8:0] sel, output qq);".format(len(dffs)-1))
print("    wire clkn, lsrn, cen;")
print("    INV clk_inv (.A(clk), .Z(clkn));")
print("    INV lsr_inv (.A(lsr), .Z(lsrn));")
print("    INV ce_inv (.A(ce), .Z(cen));")
print("    wire [{}:0] q;".format(len(dffs)))
print("    assign qq = q[sel];")
print("    {}".format("\n    ".join(dffs)))
print("endmodule")
