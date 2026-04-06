(* \db:architecture ="LIFCL", \db:device ="LIFCL-33", \db:package ="WLCSP84", \db:speed ="8_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);

   (* \xref:LOG ="q_c@0@9"${arcs_attr} *)   
   wire q;
   
    (* \dm:primitive ="OSC_CORE", \dm:programming ="MODE:OSC_CORE ${config}", \dm:site ="OSC_CORE_R1C29" *) 
    OSC_CORE OSC_I (
	.${pin_name}( q )
   );

   	(* \dm:cellmodel_primitives ="REG0=reg", \dm:primitive ="SLICE", \dm:programming ="MODE:LOGIC Q0:Q0 ", \dm:site ="R2C2A" *) 
	SLICE SLICE_I ( ${target}  );
endmodule
