
(* \db:architecture ="LIFCL", \db:device ="LIFCL-17", \db:package ="QFN72", \db:speed ="7_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
	(* \xref:LOG ="q_c@0@9" *)
	wire foo;

    ${cmt} (* \dm:primitive ="PLL_CORE", \dm:programming ="MODE:PLL_CORE ${config}", \dm:site ="${site}" *) 
    ${cmt} PLL_CORE IP_I (.STDBY(foo), .PLLRESET(foo), .LEGACY(foo), .LOCK(foo) );

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
