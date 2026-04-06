
(* \db:architecture ="LIFCL", \db:device ="${device}", \db:package ="WLCSP84", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    ${cmt} (* \dm:primitive ="${prim}", \dm:programming ="MODE:${prim} ${config}", \dm:site ="${site}" *) 
    ${cmt} ${prim} IP_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
