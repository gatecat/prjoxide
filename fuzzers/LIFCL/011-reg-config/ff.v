
(* \db:architecture ="LIFCL", \db:device ="LIFCL-40", \db:package ="QFN72", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (

);
   	VHI vhi_i();
   
	(* \xref:LOG ="q_c@0@9", \dm:arcs ="${arc}" *)
	${q_used_comment} wire q;

	(* \dm:cellmodel_primitives ="REG${k}=i48_3_lut", \dm:primitive ="SLICE", \dm:programming ="MODE:LOGIC ${mux} REG${k}:::REGSET=${regset},SEL=${sel},LSRMODE=${lsrmode} GSR:${gsr} SRMODE:${srmode} Q0:Q0 Q1:Q1 ", \dm:site ="R2C2${z}" *)
	SLICE SLICE_I ( 
			${q_used_comment} .A0(q)
			${used} );
endmodule
