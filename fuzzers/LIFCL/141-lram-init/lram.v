
(* \db:architecture ="LIFCL", \db:device ="LIFCL-40", \db:package ="QFN72", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
   (* \dm:primitive ="LRAM_CORE", \dm:programming ="MODE:LRAM_CORE LRAM_CORE:::ECC_BYTE_SEL=BYTE_EN,INITVAL_${a}=${v}", \dm:site ="LRAM_CORE_R18C86" *) 
   LRAM_CORE LRAM_I ( );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
