print("module top(input [1:0] A, B, C, D, output [5:0] S);")
print("wire [1:0] cy;")
for i in range(3):
	print("    CCU2 #(.INIT0(\"0x1234\"), .INIT1(\"0x5678\")) SLICE_CCU_{} (".format(i))
	if i > 0:
		print("        .CIN(cy[{}]),".format(i-1))
	print("    {},".format(", ".join([".{p}0({p}[0])".format(p=p) for p in "ABCD"])))
	print("    {},".format(", ".join([".{p}1({p}[1])".format(p=p) for p in "ABCD"])))
	if i < 2:
		print("        .COUT(cy[{}]),".format(i))
	print("        .S0(S[{}]), .S1(S[{}])".format(i*2, i*2+1))
	print("    );")
print("endmodule")
