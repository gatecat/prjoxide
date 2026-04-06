
(* \db:architecture ="LIFCL", \db:device ="${dev}", \db:package ="${package}", \db:speed ="${speed_grade}_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    (* \dm:primitive ="DCC", \dm:programming ="DCC:::DCCEN=${dccen}", \dm:site ="${site}" *) 
    DCC DCC_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
