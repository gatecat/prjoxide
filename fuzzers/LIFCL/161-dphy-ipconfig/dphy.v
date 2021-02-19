
(* \db:architecture ="LIFCL", \db:device ="LIFCL-40", \db:package ="QFN72", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    (* \dm:primitive ="DPHY_CORE", \dm:programming ="MODE:DPHY_CORE DPHY_CORE:::${k}=${v}", \dm:site ="DPHY0" *) 
    DPHY_CORE IP_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
