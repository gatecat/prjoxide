// Simple bram example for the LIFCL-40-EVN board
// Use switches to set RAM write data (`w_data`)
// pushbutton 0 ("PBO") writes to BRAM
// pushbutton 1 ("PB1") reads from BRAM onto leds

// How to verify BRAM is used?
// Can check for PDPSC16K in e.g. 
// 1. bram.json 
// 2. nextpnr-nexus output
// 2. `show` in yosys (after `synth_nexus`)

module top(input clk,
           input [7:0] sw,
           input [1:0] button,
           output [13:0] led);

    //// //// //// ////  RAM
    localparam RAM_WIDTH = 8;
    localparam RAM_DEPTH = 256;
    localparam ADDR_WIDTH = 8;
    reg [(RAM_WIDTH-1):0] ram [0:(RAM_DEPTH-1)]; 
    wire [(RAM_WIDTH-1):0] w_data;
    reg [(RAM_WIDTH-1):0] r_data;
    reg [(ADDR_WIDTH-1):0] w_addr;
    reg [(ADDR_WIDTH-1):0] r_addr;
    wire w_en;
    wire r_en; 
    always @(posedge clk) begin
        if (w_en) begin
            ram[w_addr] <= w_data;
        end
    end
    always @(posedge clk) begin
        if (r_en)
            r_data <= ram[r_addr];
    end
    //// //// //// ////  RAM
    
    //// LIFCL-40-EVN Assignments
    assign w_en = ~button[0];
    assign r_en = ~button[1];
    assign w_data = sw;
    assign led[13:RAM_WIDTH] = {14-RAM_WIDTH{1'b1}};
    assign led[RAM_WIDTH-1:0] = ~(w_en ? sw : r_data);

    //// Address increment to prevent synthesis
    // from simplifying bram away
    always @(posedge clk) begin
        if (w_en) begin
            w_addr <= w_addr + 10'd1;
        end
    end

    always @(posedge clk) begin
        if (r_en) begin
            r_addr <= r_addr + 10'd1;
        end
    end

    //// //// //// ////  RAM
    initial begin
        ram[0] = 8'd0;
        ram[1] = 8'd0;
        ram[2] = 8'd0;
        ram[3] = 8'd0;
        ram[4] = 8'd0;
        ram[5] = 8'd0;
        ram[6] = 8'd0;
        ram[7] = 8'd0;
        ram[8] = 8'd0;
        ram[9] = 8'd0;
        ram[10] = 8'd0;
        ram[11] = 8'd0;
        ram[12] = 8'd0;
        ram[13] = 8'd0;
        ram[14] = 8'd0;
        ram[15] = 8'd0;
        ram[16] = 8'd0;
        ram[17] = 8'd0;
        ram[18] = 8'd0;
        ram[19] = 8'd0;
        ram[20] = 8'd0;
        ram[21] = 8'd0;
        ram[22] = 8'd0;
        ram[23] = 8'd0;
        ram[24] = 8'd0;
        ram[25] = 8'd0;
        ram[26] = 8'd0;
        ram[27] = 8'd0;
        ram[28] = 8'd0;
        ram[29] = 8'd0;
        ram[30] = 8'd0;
        ram[31] = 8'd0;
        ram[32] = 8'd0;
        ram[33] = 8'd0;
        ram[34] = 8'd0;
        ram[35] = 8'd0;
        ram[36] = 8'd0;
        ram[37] = 8'd0;
        ram[38] = 8'd0;
        ram[39] = 8'd0;
        ram[40] = 8'd0;
        ram[41] = 8'd0;
        ram[42] = 8'd0;
        ram[43] = 8'd0;
        ram[44] = 8'd0;
        ram[45] = 8'd0;
        ram[46] = 8'd0;
        ram[47] = 8'd0;
        ram[48] = 8'd0;
        ram[49] = 8'd0;
        ram[50] = 8'd0;
        ram[51] = 8'd0;
        ram[52] = 8'd0;
        ram[53] = 8'd0;
        ram[54] = 8'd0;
        ram[55] = 8'd0;
        ram[56] = 8'd0;
        ram[57] = 8'd0;
        ram[58] = 8'd0;
        ram[59] = 8'd0;
        ram[60] = 8'd0;
        ram[61] = 8'd0;
        ram[62] = 8'd0;
        ram[63] = 8'd0;
        ram[64] = 8'd0;
        ram[65] = 8'd0;
        ram[66] = 8'd0;
        ram[67] = 8'd0;
        ram[68] = 8'd0;
        ram[69] = 8'd0;
        ram[70] = 8'd0;
        ram[71] = 8'd0;
        ram[72] = 8'd0;
        ram[73] = 8'd0;
        ram[74] = 8'd0;
        ram[75] = 8'd0;
        ram[76] = 8'd0;
        ram[77] = 8'd0;
        ram[78] = 8'd0;
        ram[79] = 8'd0;
        ram[80] = 8'd0;
        ram[81] = 8'd0;
        ram[82] = 8'd0;
        ram[83] = 8'd0;
        ram[84] = 8'd0;
        ram[85] = 8'd0;
        ram[86] = 8'd0;
        ram[87] = 8'd0;
        ram[88] = 8'd0;
        ram[89] = 8'd0;
        ram[90] = 8'd0;
        ram[91] = 8'd0;
        ram[92] = 8'd0;
        ram[93] = 8'd0;
        ram[94] = 8'd0;
        ram[95] = 8'd0;
        ram[96] = 8'd0;
        ram[97] = 8'd0;
        ram[98] = 8'd0;
        ram[99] = 8'd0;
        ram[100] = 8'd0;
        ram[101] = 8'd0;
        ram[102] = 8'd0;
        ram[103] = 8'd0;
        ram[104] = 8'd0;
        ram[105] = 8'd0;
        ram[106] = 8'd0;
        ram[107] = 8'd0;
        ram[108] = 8'd0;
        ram[109] = 8'd0;
        ram[110] = 8'd0;
        ram[111] = 8'd0;
        ram[112] = 8'd0;
        ram[113] = 8'd0;
        ram[114] = 8'd0;
        ram[115] = 8'd0;
        ram[116] = 8'd0;
        ram[117] = 8'd0;
        ram[118] = 8'd0;
        ram[119] = 8'd0;
        ram[120] = 8'd0;
        ram[121] = 8'd0;
        ram[122] = 8'd0;
        ram[123] = 8'd0;
        ram[124] = 8'd0;
        ram[125] = 8'd0;
        ram[126] = 8'd0;
        ram[127] = 8'd0;
        ram[128] = 8'd0;
        ram[129] = 8'd0;
        ram[130] = 8'd0;
        ram[131] = 8'd0;
        ram[132] = 8'd0;
        ram[133] = 8'd0;
        ram[134] = 8'd0;
        ram[135] = 8'd0;
        ram[136] = 8'd0;
        ram[137] = 8'd0;
        ram[138] = 8'd0;
        ram[139] = 8'd0;
        ram[140] = 8'd0;
        ram[141] = 8'd0;
        ram[142] = 8'd0;
        ram[143] = 8'd0;
        ram[144] = 8'd0;
        ram[145] = 8'd0;
        ram[146] = 8'd0;
        ram[147] = 8'd0;
        ram[148] = 8'd0;
        ram[149] = 8'd0;
        ram[150] = 8'd0;
        ram[151] = 8'd0;
        ram[152] = 8'd0;
        ram[153] = 8'd0;
        ram[154] = 8'd0;
        ram[155] = 8'd0;
        ram[156] = 8'd0;
        ram[157] = 8'd0;
        ram[158] = 8'd0;
        ram[159] = 8'd0;
        ram[160] = 8'd0;
        ram[161] = 8'd0;
        ram[162] = 8'd0;
        ram[163] = 8'd0;
        ram[164] = 8'd0;
        ram[165] = 8'd0;
        ram[166] = 8'd0;
        ram[167] = 8'd0;
        ram[168] = 8'd0;
        ram[169] = 8'd0;
        ram[170] = 8'd0;
        ram[171] = 8'd0;
        ram[172] = 8'd0;
        ram[173] = 8'd0;
        ram[174] = 8'd0;
        ram[175] = 8'd0;
        ram[176] = 8'd0;
        ram[177] = 8'd0;
        ram[178] = 8'd0;
        ram[179] = 8'd0;
        ram[180] = 8'd0;
        ram[181] = 8'd0;
        ram[182] = 8'd0;
        ram[183] = 8'd0;
        ram[184] = 8'd0;
        ram[185] = 8'd0;
        ram[186] = 8'd0;
        ram[187] = 8'd0;
        ram[188] = 8'd0;
        ram[189] = 8'd0;
        ram[190] = 8'd0;
        ram[191] = 8'd0;
        ram[192] = 8'd0;
        ram[193] = 8'd0;
        ram[194] = 8'd0;
        ram[195] = 8'd0;
        ram[196] = 8'd0;
        ram[197] = 8'd0;
        ram[198] = 8'd0;
        ram[199] = 8'd0;
        ram[200] = 8'd0;
        ram[201] = 8'd0;
        ram[202] = 8'd0;
        ram[203] = 8'd0;
        ram[204] = 8'd0;
        ram[205] = 8'd0;
        ram[206] = 8'd0;
        ram[207] = 8'd0;
        ram[208] = 8'd0;
        ram[209] = 8'd0;
        ram[210] = 8'd0;
        ram[211] = 8'd0;
        ram[212] = 8'd0;
        ram[213] = 8'd0;
        ram[214] = 8'd0;
        ram[215] = 8'd0;
        ram[216] = 8'd0;
        ram[217] = 8'd0;
        ram[218] = 8'd0;
        ram[219] = 8'd0;
        ram[220] = 8'd0;
        ram[221] = 8'd0;
        ram[222] = 8'd0;
        ram[223] = 8'd0;
        ram[224] = 8'd0;
        ram[225] = 8'd0;
        ram[226] = 8'd0;
        ram[227] = 8'd0;
        ram[228] = 8'd0;
        ram[229] = 8'd0;
        ram[230] = 8'd0;
        ram[231] = 8'd0;
        ram[232] = 8'd0;
        ram[233] = 8'd0;
        ram[234] = 8'd0;
        ram[235] = 8'd0;
        ram[236] = 8'd0;
        ram[237] = 8'd0;
        ram[238] = 8'd0;
        ram[239] = 8'd0;
        ram[240] = 8'd0;
        ram[241] = 8'd0;
        ram[242] = 8'd0;
        ram[243] = 8'd0;
        ram[244] = 8'd0;
        ram[245] = 8'd0;
        ram[246] = 8'd0;
        ram[247] = 8'd0;
        ram[248] = 8'd0;
        ram[249] = 8'd0;
        ram[250] = 8'd0;
        ram[251] = 8'd0;
        ram[252] = 8'd0;
        ram[253] = 8'd0;
        ram[254] = 8'd0;
        ram[255] = 8'd0;
    end
    //// //// //// ////  RAM

endmodule

