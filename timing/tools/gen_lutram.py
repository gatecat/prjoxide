print("""
module top(input clk, wre, input [3:0] wad, rad, wd, output [3:0] rd);

reg [3:0] mem[0:15];

always @(posedge clk) if(wre) mem[wad] <= wd;

assign rd = mem[rad];

endmodule
""")
