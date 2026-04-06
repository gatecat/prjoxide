
(* \db:architecture ="LIFCL", \db:device ="${device}", \db:package ="${package}", \db:speed ="${speed_grade}_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    
);
    (* \dm:primitive ="${s}IOLOGIC_CORE", \dm:programming ="MODE:${mode} ${config}", \dm:site ="${site}" *) 
    ${s}IOLOGIC_CORE EBR_I (${pinconn} );
${sig}
    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();
endmodule
