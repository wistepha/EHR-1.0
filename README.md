# EHR-1.0
Includes files mentioned in the MSc thesis "Electrical High Rate Setup"

-----------------------------------------------------
####A description of the files found in this repository:
-----------------------------------------------------

* EHR.PcbDoc
> PCB design file (ALTIUM designer)

* EHR.SchDoc
> PCB schematic file (ALTIUM designer)

* finalv3_1_top.rbf
> Raw binary file of the FPGA design. It can be used to configure the FPGA via the FrontPanel interface.

* finalv3_1_top.v
> Verilog file of the FPGA design.

* flash_reset.cpp
> Loads  the boot reset profile of the ZEM4314 board. The file's name and path must be specified in the program.

* FPGA.py
> The FPGA class. It facilitates the use of the ZEM4310 board. Works only if ok.py is available.

* FPGA_test.py
> A simple testbench for the ZEM4310 used for debugging. Many of it's functions are obsolete.

* Pattern_init.mif
> Memory initialisation file used in finalv3_1_top.v. It initialises the pattern memory to all 0.

* select_init.mif
> Memory initialisation file used in finalv3_1_top.v. It initialises the wire select memory to all 1.

* write_mem_file.py
> Simple program to write text files used by FPGA.py to write into the FPGA pattern memory.

* location.py
> Sends pulses (randomly) through individual wires while sending triggers. Maps the location of the clusters.

* map.py
> Basic test. Sends triggers and collects some data of the read out.
