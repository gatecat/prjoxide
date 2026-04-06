(* \db:architecture ="${arch}", \db:device ="${device}", \db:package ="${package}", \db:speed ="${speed_grade}_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    ${cmt} ${pintype} q
);

    // A primitive is needed, but VHI should be harmless
    (* \xref:LOG ="q_c@0@9" *)
    VHI vhi_i();

    ${cmt}(*  \dm:primitive ="${primtype}", \dm:programming ="MODE:${primtype} ${primtype}:::IO_TYPE=${iotype},BANK_VCCIO=${vcc}${extra_config}:T=${t}", \dm:site ="${site}" *) 
    ${cmt}${primtype} INST  (.PADDO(q));

endmodule 
