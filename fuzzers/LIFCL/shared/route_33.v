(* \db:architecture ="LIFCL", \db:device ="LIFCL-33", \db:package ="WLCSP84", \db:speed ="8_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (

);
	(* \xref:LOG ="q_c@0@9"${arcs_attr} *)
	wire q;
   
	(* \dm:cellmodel_primitives ="REG0=reg", \dm:primitive ="SLICE", \dm:programming ="MODE:LOGIC Q0:Q0 ", \dm:site ="R2C2A" *) 
	SLICE SLICE_I ( .A0(q), .Q0(q)  );
endmodule
