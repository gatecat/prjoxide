(* \db:architecture ="${arch}", \db:device ="${device}", \db:package ="${package}", \db:speed ="${speed_grade}_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    ${cmt} (* \dm:primitive ="OSCD_CORE", \dm:programming ="MODE:OSCD_CORE ${config}", \dm:site ="${site}" *)
    ${cmt} OSCD_CORE OSC_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
