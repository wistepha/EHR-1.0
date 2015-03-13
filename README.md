# EHR-1.0
Includes files mentioned in the MSc thesis "Electrical High Rate Setup"

-----------------------------------------------------
####A description of the files found in this repository:
-----------------------------------------------------

* ana-run4-add1.root
> Contains the analysis of the second run of measurements performed at a trigger rate of 100 kHz and a WBC of 249.

* ana-wbc-XX-new.root
> Contains the analysis of all measurements done with a WBC value of XX.

* DTB.py
> Contains the commands used to control the DTB. The adc() command and the read out sequence are particular to this file.

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

* functions.py
> Contains some functions used in map.py

* location.py
> Sends pulses (randomly) through individual wires while sending triggers. Maps the location of the clusters.

* map.py
> Basic test. Sends triggers and collects some data of the read out, including the pixel address and the pulse height.

* multi-scan-extana.py
> Performs the same analysis which multi-scan.py performs. extana2 allows to change the data file for each data point. This was used to combine the analysis of multi-scan-runX.root and multi-scan-runX-addY.root files.

* multi-scan-runX-addY.root
> Contain the efficiency maps for the measurement runs. The -add files contain measurements to substitute the last measurements of the original run file due to measurement errors.
> - run1: WBC = 100
> - run2: WBC = 150
> - run3: WBC = 50,249 | trigger rate = 10 kHz
> - run4: WBC = 249 | trigger rates: 30 kHz, 60 kHz, 100 kHz

* param.py
> Contains parameters used in map.py

* Pattern_init.mif
> Memory initialisation file used in finalv3_1_top.v. It initialises the pattern memory to all 0.

* rateXX.root
> Contains hits per event distributions for individual wires. The measurements were performed with a rate parameter of XX. The phase shift performed, if mentioned in the file name, was 10.4 ns.

* select_init.mif
> Memory initialisation file used in finalv3_1_top.v. It initialises the wire select memory to all 1.

* write_mem_file.py
> Simple program to write text files used by FPGA.py to write into the FPGA pattern memory.


