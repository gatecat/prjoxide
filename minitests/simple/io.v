module top(
	 input a,
 	output y);

	wire a_buf;
	(* LOC="P11", IO_TYPE="LVCMOS10", PULLMODE="UP" *)
	IB ib_a(.I(a), .O(a_buf));

	(* LOC="P10", IO_TYPE="LVCMOS18H" *)
	OB ob_y(.I(a_buf), .O(y));
endmodule
