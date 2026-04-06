
(* \db:architecture ="LIFCL", \db:device ="LIFCL-33", \db:package ="WLCSP84", \db:speed ="8_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    ${cmt} (* \dm:primitive ="OSC_CORE", \dm:programming ="MODE:OSC_CORE ${config}", \dm:site ="OSC_CORE_R1C29" *) 
    ${cmt} OSC_CORE OSC_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
