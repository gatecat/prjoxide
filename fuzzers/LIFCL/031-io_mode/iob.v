(* \db:architecture ="${arch}", \db:device ="${device}", \db:package ="${package}", \db:speed ="${speed_grade}_High-Performance_1.0V", \db:timestamp =1576073342, \db:view ="physical" *)
module top (
    ${cmt} ${pintype} q
);

    VHI vhi_i();
   
    ${cmt}(* \xref:LOG ="${primtype}=q_pad.bb_inst@0@8", \dm:cellmodel_primitives ="${primtype}=q_pad.bb_inst", \dm:primitive ="${primtype}", \dm:programming ="MODE:${primtype} ${primtype}:::IO_TYPE=${iotype},BANK_VCCIO=${vcc}${extra_config}:T=${t}", \dm:site ="${site}" *) 
    ${cmt}${primtype} \q_pad.bb_inst  (.PADDO(q));

endmodule
