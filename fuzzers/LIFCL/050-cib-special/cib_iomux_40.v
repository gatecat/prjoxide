
(* \db:architecture ="LIFCL", \db:device ="LIFCL-40", \db:package ="QFN72", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (

);
	(* \xref:LOG ="q_c@0@9"${arcs_attr} *)
	wire q;

	(* \xref:LOG ="q_c@0@10", \dm:arcs ="${extra_arc}" *)
	wire q2;

	(* \dm:cellmodel_primitives ="REG0=reg", \dm:primitive ="SLICE", \dm:programming ="MODE:LOGIC Q0:Q0 ", \dm:site ="R2C2A" *) 
	SLICE SLICE_I ( .A0(q), .Q0(q), .A1(q2), .Q1(q2) );
endmodule
