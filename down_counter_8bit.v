module down_counter_8bit (
    input        clk,
    input        rst_n,   // reset attivo basso
    input        en,      // enable
    output [7:0] count
);

    reg [7:0] count_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count_reg <= 8'd255;          // Reset a 255 invece di 0
        else if (en)
            count_reg <= count_reg - 8'd1; // Sottrazione invece di addizione
    end

    assign count = count_reg;

endmodule
