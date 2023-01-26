// Simple lram + blinky example for the LIFCL-40-EVN board

module top(input gsrn, clk, addr_en, wr_en,
           output [13:0] led);

    (* ram_style="huge" *) reg [15:0] ram [0:1023];  // or use (* lram *)
    reg [15:0] rd_lram; 

    reg [13:0] shift = 0;
    reg [20:0] div;
    reg clkdiv;
    reg dir = 0;
    reg [9:0] addr;

    always @(posedge clk) begin
        // Generate a slow clock
        {clkdiv, div} <= div + 1'b1;
        // Scan the LED back and forth
        if (clkdiv) begin
            if (shift[13])
                dir = 1'b1;
            else if (shift[0])
                dir = 1'b0;

            if (!(|shift))
                shift <= 14'b1;
            else if (dir)
                shift <= {shift[0], shift[13:1]};
            else
                shift <= {shift[12:0], shift[13]};

            if (~wr_en) begin // SW 3 (default high, low when pressed)
                rd_lram <= ram[addr];
            end else begin
                ram[addr] <= {shift[13:12], shift};
            end
            if (~addr_en) begin // SW 2 
                addr <= addr + 1'b1;
            end
        end

        if (!gsrn) begin
            rd_lram <= 16'b0;
            addr <= 10'b0;
            dir <= 1'b0;
            shift <= 14'b0;
            div <= 21'b0;
            clkdiv <= 1'b0;
        end
    end

    // LEDs are active low 
    assign led = ~(shift | addr | rd_lram[13:0]);

endmodule
