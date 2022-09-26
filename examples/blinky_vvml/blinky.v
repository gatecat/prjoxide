// Simple blinky example for the LIFCL-40-VVML board

module top(input gsrn, output [3:0] led);
	wire clk;

	// Internal oscillator
	OSC_CORE #(
		.HF_CLK_DIV("16")
	) osc_i (
		.HFOUTEN(1'b1),
		.HFCLKOUT(clk)
	);

	reg [3:0] shift = 0;
	reg [20:0] div;
	reg clkdiv;
	reg dir = 0;

	always @(posedge clk) begin
		// Generate a slow clock
		{clkdiv, div} <= div + 1'b1;
		// Scan the LED back and forth
		if (clkdiv) begin
			if (shift[3])
				dir = 1'b1;
			else if (shift[0])
				dir = 1'b0;

			if (!(|shift))
				shift <= 4'b1;
			else if (dir)
				shift <= {shift[0], shift[3:1]};
			else
				shift <= {shift[2:0], shift[3]};
		end
		if (!gsrn) begin
			// Reset
			dir <= 1'b0;
			shift <= 4'b0;
			div <= 21'b0;
			clkdiv <= 1'b0;
		end
	end

	// LEDs are active low
	assign led = ~shift;

endmodule
