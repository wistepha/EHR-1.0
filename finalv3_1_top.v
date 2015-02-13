//finalv3_1.v

module cable_random(clk, reset, rate, pulse);

	input clk;
	input reset;
	input rate;
	output pulse;

	wire clk;
	wire reset;
	wire [31:0]rate;
	reg pulse;	
	wire [31:0]s;
	wire cmp_out;
	reg comp_out;
	
	reg [31:0]sa;
	reg [31:0]sb;
	reg [31:0]sc;
	parameter sa_start = 32'hc48de01b;
	parameter sb_start = 32'hef71fbb1;
	parameter sc_start = 32'ha8c934e5;
	initial
	begin
		sa <= sa_start;
		sb <= sb_start;
		sc <= sc_start;
	end

	reg [4:0]state = 0;
	parameter zero = 5'b00000;
	parameter one = 5'b10011;
	parameter two = 5'b10101;
	parameter three = 5'b10111;
	parameter four = 5'b11000;
	parameter five = 5'b11010;
	parameter six = 5'b11110;
	
	wire busy;
	wire [2:0]count;
	wire signal;
	
	assign {busy, count, signal} = state;
	
	always @(posedge clk or posedge reset)
	begin
		if (reset)
		begin
		sa <= sa_start;
		sb <= sb_start;
		sc <= sc_start;
		state <= zero;
		pulse <= 0;
		end
		else
		begin
		sa <= {sa[19:1], sa[18:6]  ^ sa[31:19]};
		sb <= {sb[27:3], sb[29:23] ^ sb[31:25]};
		sc <= {sc[14:4], sc[28:8]  ^ sc[31:11]};
		pulse <= signal;	
		
		case(state)
			zero:
				if (cmp_out)
				begin
					state <= one;
				end
			one:
				state <= two;
			two:
				state <= three;
			three:
				state <= four;
			four:
				state <= five;
			five:
				state <= six;
			six:
				state <= zero;
		endcase		
		end
	end
	assign s = sa ^ sb ^ sc;	
	
	lpm_compare comp
	(
			.clock (clk),
			.dataa (s),
			.datab (rate),
			.alb (cmp_out),
			.aclr (),
			.aeb (),
			.agb (),
			.ageb (),
			.aleb (),
			.aneb (),
			.clken ()
	);
	defparam
		comp.lpm_pipeline = 1,
		comp.lpm_representation = "UNSIGNED",
		comp.lpm_type = "LPM_COMPARE",
		comp.lpm_width = 32;
		
endmodule

module cable_pattern(clk, wena_mem, count_mod, mem_data, mem_data_addr, trigger_in, pattern_max, pattern_count_ena, pulse);

	input clk;
	input wena_mem;
	input count_mod;
	input mem_data;
	input mem_data_addr;
	input trigger_in;
	input pattern_max;
	input pattern_count_ena;
	output pulse;
	
	wire clk;
	wire wena_mem;
	wire [11:0]count_mod;
	wire [31:0]mem_data;
	wire [14:0]mem_data_addr;
	wire trigger_in;
	reg [158:0]pulse;
	
	reg [11:0] count_temp = 0;
	wire [11:0] count_out;
	wire [255:0] mem_temp;
	wire [255:0] mem_out = mem_temp[255:0];
	
	reg [7:0] pattern_count;
	wire [7:0] pattern_max;
	wire pattern_count_ena;
	
	assign count_out = count_temp;
	
	always @(posedge clk)
	begin
	
		if (pattern_count_ena)
		begin
			if (trigger_in === 1)
			begin
				pulse <= 0;
				count_temp <= 0;
				pattern_count <= 0;
			end
			
			else if (pattern_count < pattern_max)
			begin
				pulse <= mem_out[158:0];
				if (count_temp == count_mod)
				begin
					count_temp <= 0;
					pattern_count <= pattern_count + 1;
				end
						
				else
					count_temp <= count_temp + 1;
			end
			else
				pulse <= 0;
		end
		
		else
		begin
			pulse <= mem_out[158:0];
			
			if (count_temp == count_mod || trigger_in === 1)
				count_temp <= 0;
			else
				count_temp <= count_temp + 1;
		end

	end
	
//	lpm_counter	LPM_COUNTER_component (
//				.clock (clk),
//				.q (count_out),
//				.aclr (1'b0),
//				.aload (1'b0),
//				.aset (1'b0),
//				.cin (1'b1),
//				.clk_en (1'b1),
//				.cnt_en (1'b1),
//				.cout (),
//				.data ({7{1'b0}}),
//				.eq (),
//				.sclr (1'b0),
//				.sload (1'b0),
//				.sset (1'b0),
//				.updown (1'b1));
//	defparam
//		LPM_COUNTER_component.lpm_direction = "UP",
//		//LPM_COUNTER_component.lpm_modulus = 82,
//		LPM_COUNTER_component.lpm_port_updown = "PORT_UNUSED",
//		LPM_COUNTER_component.lpm_type = "LPM_COUNTER",
//		LPM_COUNTER_component.lpm_width = 7;	

	altsyncram	mem (
				.address_a (mem_data_addr),
				.clock0 (clk),
				.data_a (mem_data),
				.wren_a (wena_mem),
				.address_b (count_out),
				.q_b (mem_temp),
				.aclr0 (1'b0),
				.aclr1 (1'b0),
				.addressstall_a (1'b0),
				.addressstall_b (1'b0),
				.byteena_a (1'b1),
				.byteena_b (1'b1),
				.clock1 (1'b1),
				.clocken0 (1'b1),
				.clocken1 (1'b1),
				.clocken2 (1'b1),
				.clocken3 (1'b1),
				.data_b ({256{1'b1}}),
				.eccstatus (),
				.q_a (),
				.rden_a (1'b1),
				.rden_b (1'b1),
				.wren_b (1'b0));
	defparam
		mem.address_aclr_b = "NONE",
		mem.address_reg_b = "CLOCK0",
		mem.clock_enable_input_a = "BYPASS",
		mem.clock_enable_input_b = "BYPASS",
		mem.clock_enable_output_b = "BYPASS",
		mem.init_file = "Pattern_init.mif",
		mem.init_file_layout = "PORT_B",
		mem.intended_device_family = "Cyclone IV E",
		mem.lpm_type = "altsyncram",
		mem.numwords_a = 32768,
		mem.numwords_b = 4096,
		mem.operation_mode = "DUAL_PORT",
		mem.outdata_aclr_b = "NONE",
		mem.outdata_reg_b = "CLOCK0",
		mem.power_up_uninitialized = "FALSE",
		mem.read_during_write_mode_mixed_ports = "OLD_DATA",
		mem.widthad_a = 15,
		mem.widthad_b = 12,
		mem.width_a = 32,
		mem.width_b = 256,
		mem.width_byteena_a = 1;
		
endmodule

module phshift(intclk, reset, phsmax, dyn_phase, counter, phasecounterselect, phaseupdown, phasestep, phasedone);

input intclk;
input reset;
input [6:0] phsmax;
input [2:0] counter;
input phasedone;
input [1:0] dyn_phase;

output [2:0] phasecounterselect;
output phaseupdown;
output phasestep;

wire intclk;
wire reset;
wire [6:0] phsmax;
wire [2:0] counter;
wire phasedone;
wire [1:0] dyn_phase;
reg [2:0] phasecounterselect;
reg phaseupdown;
reg phasestep;

reg [1:0] phstate;
reg [1:0] next_phstate;
reg [2:0] count;
reg [6:0] phscount;
reg step;

parameter phase_up=2'b01, phase_down=2'b10, do_nothing=2'b00, up=1'b1, down=1'b0;

always @ (posedge intclk) 
	begin
		phstate <= next_phstate;
		if (reset) 
			begin
			count <= 0;
			phasestep <= 1'b0;
			phaseupdown = 1'b0;
			phasecounterselect <= 0;
			phscount <= 0;
			end
		else
		begin
			if (phstate == do_nothing)
				phscount <= 0;
			if (phscount < phsmax)
			begin
				if (phstate == phase_up) step = up;
				if (phstate == phase_down) step = down;
			
				if (phstate !=  do_nothing && count == 0 && phasedone) 
				begin
					phaseupdown <= step;
					phasecounterselect = counter;
					count <= count + 1;
				end
				if (count == 1) 
				begin
					phasestep <= 1'b1;
					count <= count + 1;
				end				
				if (count == 2) 
				begin
					count <= count + 1;
				end
				if (count == 3) 
				begin
					count <= count + 1;
				end
				if (count == 4)
				begin
					phasestep <= 1'b0;
					count <= count + 1;
				end
				if (count >= 5)
				begin
					phaseupdown <= 1'b0;
					phasecounterselect = 0;
					count <= count + 1;
				end
				if (count == 7) 
				begin
					count <= 0;
					phscount <= phscount + 1;
				end
			end
		end
	end

always @(posedge intclk)
	begin
	case (dyn_phase)
		2'b01:
			next_phstate = phase_up;
		2'b10:
			next_phstate = phase_down;
		default:
			next_phstate = do_nothing;
	endcase
	end
endmodule

module finalv3_1_top(
	input  wire [4:0]   okUH,
	output wire [2:0]   okHU,
	inout  wire [31:0]  okUHU,
	inout  wire         okAA,
	input  wire         sys_clk,
	input  wire         ext_clk,
	input  wire         trigger_in,
	output wire [158:0] cable,
	output wire         led
	); 

	
	wire [31:0]rate;
	wire patternena;
	wire [158:0]cable_ran;
	wire [158:0]cable_def;
	wire [1:0]in_clk = {sys_clk,ext_clk};
	reg [158:0]cable_temp;
	wire ran_reset;
	wire somereset;
	//PLL
	wire pllreset;
	wire locked;
	tri0 clockswitch;
	wire activeclock;
	wire clk;
	//dynamic phase shift
	wire [6:0] phsmax;
	wire [2:0] phasecounterselect;
	wire phaseupdown;
	wire phasestep;
	wire phasedone;
	wire [1:0]phsphase;
	wire [2:0]phscounter;
	
	//select
	wire [255:0]select_temp;
	reg [255:0]select;
	wire wena_sel;
	wire read_sel;
	wire [31:0]sel_data;
	wire [3:0]sel_data_addr;
	
	//mem
	wire wena_mem;
	wire [11:0]count_mod;
	wire [31:0]mem_data;
	wire [14:0]mem_data_addr;
	wire [7:0]pattern_max;
	wire pattern_count_ena;
	
	//FrontPanel Communication
	wire         okClk;
	wire [112:0] okHE;
	wire [64:0]  okEH;
	
	wire [31:0]ep00wire;//patternena
	wire [31:0]ep01wire;//rate
	wire [31:0]ep02wire;//select
	wire [31:0]ep03wire;
	wire [31:0]ep04wire;//mem
	wire [31:0]ep05wire;
	wire [31:0]ep06wire;//count_mod
	wire [31:0]ep07wire;//clockswitch & pllreset
	wire [31:0]ep20wire;//pulses
	wire [31:0]ep21wire;
	wire [31:0]ep22wire;
	wire [31:0]ep23wire;
	wire [31:0]ep24wire;//pulses + activeclock
	wire [31:0]ep25wire;//pll locked
	
	assign {pattern_max, pattern_count_ena, patternena} = ep00wire[9:0];
	assign rate = ep01wire;
	assign {sel_data_addr, wena_sel, read_sel} = ep02wire[5:0];
	assign sel_data = ep03wire;
	assign {mem_data_addr, wena_mem} = ep04wire[15:0];
	assign mem_data = ep05wire;
	assign count_mod = ep06wire[11:0];
	assign {phsmax,ran_reset,somereset,phsphase,phscounter,pllreset,clockswitch} = ep07wire[15:0];
	assign {ep20wire,ep21wire,ep22wire,ep23wire,ep24wire} = {activeclock,cable_temp};
	assign ep25wire[1:0] = {phasedone,locked};
	assign led = ~activeclock;
	assign cable = cable_temp;	
	// [\Front Panel]

	always @(posedge clk)
	begin
	select <= select_temp;
		if (patternena)
		begin
			cable_temp <= (cable_def & select[158:0]);
		end
		else
		begin
			cable_temp <= (cable_ran & select[158:0]);
		end
	end
	
	// generates cables for random pattern
	genvar i;
	generate
		for(i=0;i<159;i=i+1) begin: RANDOMPAT
	cable_random #(32'hc48de01b+i*10,32'hef71fbb1+i*9,32'ha8c934e5+i*8,5'b00000,5'b10011,5'b10101,5'b10111,5'b11000,5'b11010,5'b11110)cable_ran_inst(.clk(clk),.reset(ran_reset),.rate(rate),.pulse(cable_ran[i]));
	end
	endgenerate
	
	// calls module to create user-defined pattern
	cable_pattern cable_def_inst(.clk(clk), .wena_mem(wena_mem), .count_mod(count_mod), .mem_data(mem_data), .mem_data_addr(mem_data_addr), .trigger_in(trigger_in), .pattern_max(pattern_max), .pattern_count_ena(pattern_count_ena), .pulse(cable_def));
	
	// state machine as an agent to control the phase shift feature of the pll
	phshift #(2'b01,2'b10,2'b00,1'b1,1'b0)phshift_inst(.intclk(sys_clk), .reset(pllreset), .phsmax(phsmax), .dyn_phase(phsphase), .counter(phscounter), .phasecounterselect(phasecounterselect), .phaseupdown(phaseupdown), .phasestep(phasestep), .phasedone(phasedone));
	
	//select
	altsyncram	select_mem (
				.address_a (sel_data_addr),
				.clock0 (clk),
				.data_a (sel_data),
				.wren_a (wena_sel),
				.address_b (read_sel),
				.q_b (select_temp),
				.aclr0 (1'b0),
				.aclr1 (1'b0),
				.addressstall_a (1'b0),
				.addressstall_b (1'b0),
				.byteena_a (1'b1),
				.byteena_b (1'b1),
				.clock1 (1'b1),
				.clocken0 (1'b1),
				.clocken1 (1'b1),
				.clocken2 (1'b1),
				.clocken3 (1'b1),
				.data_b ({256{1'b1}}),
				.eccstatus (),
				.q_a (),
				.rden_a (1'b1),
				.rden_b (1'b1),
				.wren_b (1'b0));
	defparam
		select_mem.address_aclr_b = "NONE",
		select_mem.address_reg_b = "CLOCK0",
		select_mem.clock_enable_input_a = "BYPASS",
		select_mem.clock_enable_input_b = "BYPASS",
		select_mem.clock_enable_output_b = "BYPASS",
		select_mem.init_file = "select_init.mif",
		select_mem.init_file_layout = "PORT_B",
		select_mem.intended_device_family = "Cyclone IV E",
		select_mem.lpm_type = "altsyncram",
		select_mem.numwords_a = 16,
		select_mem.numwords_b = 2,
		select_mem.operation_mode = "DUAL_PORT",
		select_mem.outdata_aclr_b = "NONE",
		select_mem.outdata_reg_b = "CLOCK0",
		select_mem.power_up_uninitialized = "FALSE",
		select_mem.read_during_write_mode_mixed_ports = "OLD_DATA",
		select_mem.widthad_a = 4,
		select_mem.widthad_b = 1,
		select_mem.width_a = 32,
		select_mem.width_b = 256,
		select_mem.width_byteena_a = 1;
		
		
	altpll	pll (
				.areset (pllreset),
				.clkswitch (clockswitch),
				.inclk (in_clk),
				.phasecounterselect (phasecounterselect),
				.phasestep (phasestep),
				.scanclk (sys_clk),
				.phaseupdown (phaseupdown),
				.activeclock (activeclock),
				.clk (clk),
				.phasedone (phasedone),
				.locked (locked),
				.clkbad (),
				.clkena ({6{1'b1}}),
				.clkloss (),
				.configupdate (1'b0),
				.enable0 (),
				.enable1 (),
				.extclk (),
				.extclkena ({4{1'b1}}),
				.fbin (1'b1),
				.fbmimicbidir (),
				.fbout (),
				.fref (),
				.icdrclk (),
				.pfdena (1'b1),
				.pllena (1'b1),
				.scanaclr (1'b0),
				.scanclkena (1'b1),
				.scandata (1'b0),
				.scandataout (),
				.scandone (),
				.scanread (1'b0),
				.scanwrite (1'b0),
				.sclkout0 (),
				.sclkout1 (),
				.vcooverrange (),
				.vcounderrange ());
	defparam
		pll.bandwidth_type = "AUTO",
		pll.clk0_divide_by = 1,
		pll.clk0_duty_cycle = 50,
		pll.clk0_multiply_by = 1,
		pll.clk0_phase_shift = "0",
		pll.compensate_clock = "CLK0",
		pll.inclk0_input_frequency = 25000,
		pll.inclk1_input_frequency = 20000,
		pll.intended_device_family = "Cyclone IV E",
		pll.lpm_hint = "CBX_MODULE_PREFIX=testpll",
		pll.lpm_type = "altpll",
		pll.operation_mode = "NORMAL",
		pll.pll_type = "AUTO",
		pll.port_activeclock = "PORT_USED",
		pll.port_areset = "PORT_USED",
		pll.port_clkbad0 = "PORT_UNUSED",
		pll.port_clkbad1 = "PORT_UNUSED",
		pll.port_clkloss = "PORT_UNUSED",
		pll.port_clkswitch = "PORT_USED",
		pll.port_configupdate = "PORT_UNUSED",
		pll.port_fbin = "PORT_UNUSED",
		pll.port_inclk0 = "PORT_USED",
		pll.port_inclk1 = "PORT_USED",
		pll.port_locked = "PORT_USED",
		pll.port_pfdena = "PORT_UNUSED",
		pll.port_phasecounterselect = "PORT_USED",
		pll.port_phasedone = "PORT_USED",
		pll.port_phasestep = "PORT_USED",
		pll.port_phaseupdown = "PORT_USED",
		pll.port_pllena = "PORT_UNUSED",
		pll.port_scanaclr = "PORT_UNUSED",
		pll.port_scanclk = "PORT_USED",
		pll.port_scanclkena = "PORT_UNUSED",
		pll.port_scandata = "PORT_UNUSED",
		pll.port_scandataout = "PORT_UNUSED",
		pll.port_scandone = "PORT_UNUSED",
		pll.port_scanread = "PORT_UNUSED",
		pll.port_scanwrite = "PORT_UNUSED",
		pll.port_clk0 = "PORT_USED",
		pll.port_clk1 = "PORT_UNUSED",
		pll.port_clk2 = "PORT_UNUSED",
		pll.port_clk3 = "PORT_UNUSED",
		pll.port_clk4 = "PORT_UNUSED",
		pll.port_clk5 = "PORT_UNUSED",
		pll.port_clkena0 = "PORT_UNUSED",
		pll.port_clkena1 = "PORT_UNUSED",
		pll.port_clkena2 = "PORT_UNUSED",
		pll.port_clkena3 = "PORT_UNUSED",
		pll.port_clkena4 = "PORT_UNUSED",
		pll.port_clkena5 = "PORT_UNUSED",
		pll.port_extclk0 = "PORT_UNUSED",
		pll.port_extclk1 = "PORT_UNUSED",
		pll.port_extclk2 = "PORT_UNUSED",
		pll.port_extclk3 = "PORT_UNUSED",
		pll.primary_clock = "inclk0",
		pll.self_reset_on_loss_lock = "OFF",
		pll.switch_over_type = "AUTO",
		pll.width_clock = 5,
		pll.width_phasecounterselect = 3;
		
		
	//Instantiating FrontPanel Communication
	wire [65*6-1:0]  okEHx;
		
	okHost okHI(
		.okUH(okUH),
		.okHU(okHU),
		.okUHU(okUHU),
		.okAA(okAA),
		.okClk(okClk),
		.okHE(okHE), 
		.okEH(okEH)
	);
	
	//.N(x), where x must match outgoing connections.
	okWireOR # (.N(6)) wireOR (okEH, okEHx);

	okWireIn     wi00(.okHE(okHE),                             .ep_addr(8'h00), .ep_dataout(ep00wire));
	okWireIn     wi01(.okHE(okHE),                             .ep_addr(8'h01), .ep_dataout(ep01wire));
	okWireIn     wi02(.okHE(okHE),                             .ep_addr(8'h02), .ep_dataout(ep02wire));
	okWireIn     wi03(.okHE(okHE),                             .ep_addr(8'h03), .ep_dataout(ep03wire));
	okWireIn     wi04(.okHE(okHE),                             .ep_addr(8'h04), .ep_dataout(ep04wire));
	okWireIn     wi05(.okHE(okHE),                             .ep_addr(8'h05), .ep_dataout(ep05wire));
	okWireIn     wi06(.okHE(okHE),                             .ep_addr(8'h06), .ep_dataout(ep06wire));
	okWireIn     wi07(.okHE(okHE),                             .ep_addr(8'h07), .ep_dataout(ep07wire));
	okWireOut    wo20(.okHE(okHE), .okEH(okEHx[ 0*65 +: 65 ]), .ep_addr(8'h20), .ep_datain(ep20wire));
	okWireOut    wo21(.okHE(okHE), .okEH(okEHx[ 1*65 +: 65 ]), .ep_addr(8'h21), .ep_datain(ep21wire));
	okWireOut    wo22(.okHE(okHE), .okEH(okEHx[ 2*65 +: 65 ]), .ep_addr(8'h22), .ep_datain(ep22wire));
	okWireOut    wo23(.okHE(okHE), .okEH(okEHx[ 3*65 +: 65 ]), .ep_addr(8'h23), .ep_datain(ep23wire));
	okWireOut    wo24(.okHE(okHE), .okEH(okEHx[ 4*65 +: 65 ]), .ep_addr(8'h24), .ep_datain(ep24wire));
	okWireOut    wo25(.okHE(okHE), .okEH(okEHx[ 5*65 +: 65 ]), .ep_addr(8'h25), .ep_datain(ep25wire));

endmodule
