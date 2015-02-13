import ok,sys,numpy,os,stat,time
from sys import argv

class ZEM:
    
    def __init__(self,serial = "",filename = "",max_modulus = 100, verbose = False):
        
        #Initialisation resets (->0) the pattern memory up to max_modulus.
        #It is recommended not to reconfigure the FPGA unless it is necessary.
        #The FPGA will only be reconfigured if filename != "".
        #The default design is assumed at "./rbfiles/finalv3_1_top.rbf"
        #It will be used if the FrontPanel interface does not react at the first attempt.
        print "\n---- Initialising the EHR ----\n"
        if max_modulus < 0 or max_modulus >= 4096:
            print "Invalid value for max_modulus. It is set to 4095."
            self.memsize = 4095
        else:
            self.memsize = max_modulus
        self.mem = numpy.zeros([256,self.memsize],dtype=numpy.int)
        self.select = numpy.ones([256,2],dtype=numpy.int)
        
        self.dev = ok.okCFrontPanel()
        self.devInfo = ok.okTDeviceInfo()
        
        if self.dev.OpenBySerial(serial) != self.dev.NoError:
            print "Device could not be opened.\nLeaving..."
            sys.exit(1)
            
        if (self.dev.NoError != self.dev.GetDeviceInfo(self.devInfo)):
            print "Error: Unable to retrieve device information."
            sys.exit(1)

        print("Found Device: " + self.devInfo.productName)
        print("Device ID: %s" % self.devInfo.deviceID)

        if filename != "":
            if self.configureFPGA(filename) == False:
                print "Unable to configure FPGA."
                sys.exit(1)
        else:
            filename = "./rbfiles/finalv3_1_top.rbf"

        #Checking for FrontPanel (USB communication) support
        for i in range(1,7):
            if self.dev.IsFrontPanelEnabled():
                print "FrontPanel is enabled."
                break
            elif i == 6:
                print "Failed to enable FrontPanel. Leaving..."
                sys.exit(1)
            else:
                print "FrontPanel disabled. Reconfiguring...",i
                self.dev.ConfigureFPGA(filename)
        
        if self.reset_pll() == False:
            print "PLL could not be resetted!"
            sys.exit(1)

        #Initialise mem to all 0
        print "Initialising memory...",
        self.mem_data_init = 0
        self.mem_addr_init = 0
        self.dev.SetWireInValue(0x05,self.mem_data_init)
        for bit in range(self.memsize):
            for addr in range(8):
                self.mem_addr_init = int(((addr + (bit*8)) *2) +1)
                self.dev.SetWireInValue(0x04,self.mem_addr_init)
                self.dev.UpdateWireIns()
        self.dev.SetWireInValue(0x04,0)
        self.dev.UpdateWireIns()

        #Initialise select to all 1
        self.sel_data_init = 0xffffffff
        self.sel_addr_init = 0
        self.dev.SetWireInValue(0x03,self.sel_data_init)
        for addr in range(16):
            self.sel_addr_init = (addr*4)+2
            self.dev.SetWireInValue(0x02,self.sel_addr_init)
            self.dev.UpdateWireIns()
        self.dev.SetWireInValue(0x02,0)
        self.dev.UpdateWireIns()

        print "Done"

        #Searching for an external clock
        print "Setting clock to external...",
        if self.set_clock(0) == True:
            print "Done"
        else:
            print "Failed\nThere is no external clock connected!"

        #Resetting the PLL and the phaseshift module
        if self.reset_pll() == False:
            print "PLL could not be resetted!"
            sys.exit(1) 
            
        if verbose:
            print "\n  Initialising wires:"
            print "        pattern_ena = 1"
            print "       trigger data = 0"
            print "     rate parameter = 256"
            print "    all memory data = 0"
            print "          count_mod = %d"%(self.memsize)
            print "\n"
        self.dev.SetWireInValue(0x00,0x00000001)
        self.dev.SetWireInValue(0x01,0x00000100)
        self.dev.SetWireInValue(0x02,0x00000000)
        self.dev.SetWireInValue(0x03,0x00000000)
        self.dev.SetWireInValue(0x04,0x00000000)
        self.dev.SetWireInValue(0x05,0x00000000)
        self.dev.SetWireInValue(0x06,self.memsize)
        self.dev.SetWireInValue(0x07,0x00000000)
        self.dev.UpdateWireIns()
        print "\n"

        self.reset_ran()
        #self.reset_phs()

        return


    def configureFPGA(self,filename = "./rbfiles/finalv3_1_top.rbf"):

        for i in range(5):
            print "\nConfiguring FPGA...",i+1
            if self.dev.ConfigureFPGA(filename) != self.dev.NoError:
                print "Reset unsuccessful. Check file path. Default: './rbfiles/finalv3_1_top.rbf'"
                return False
            else:
                #print "FPGA reset successful. File used:", filename
                if self.dev.IsFrontPanelEnabled():
                    print "\n  Initialising wires:"
                    print "        pattern_ena = 1"
                    self.dev.SetWireInValue(0x00,0x00000001)
                    print "               rate = 10"
                    self.dev.SetWireInValue(0x01,0x0000000b)
                    print "    all memory data = 0"
                    self.dev.SetWireInValue(0x02,0x00000000)
                    self.dev.SetWireInValue(0x03,0x00000000)
                    self.dev.SetWireInValue(0x04,0x00000000)
                    self.dev.SetWireInValue(0x05,0x00000000)
                    print "          count_mod = %d"%(self.memsize)
                    self.dev.SetWireInValue(0x06,self.memsize)
                    self.dev.SetWireInValue(0x07,0x00000000)
                    self.dev.UpdateWireIns()
                    print "\n"
                    return True
                else:
                    #print "FrontPanel is still not enabled."
                    time.sleep(1/4.0)
        print "Enabling FrontPanel was unsuccessful. Try again."
        sys.exit(1)


    def reset_pll(self):
        #Resets the PLL and the phase shift module.
        self.dev.SetWireInValue(0x07,2)
        self.dev.UpdateWireIns()
        time.sleep(1./1000000)
        self.dev.SetWireInValue(0x07,0)
        self.dev.UpdateWireIns()
        
        for check in range(3):
            self.dev.UpdateWireOuts()
            #0x25:  bit 1: phasedone // bit 0: locked
            self.locked = self.dev.GetWireOutValue(0x25)
            if self.locked%2 == 1:
                return True
        return False

    def reset_ran(self):
        #Resets the pseudo random number generator to its well defined starting values.
        self.dev.SetWireInValue(0x07,256)
        self.dev.UpdateWireIns()
        time.sleep(1./1000000)
        self.dev.SetWireInValue(0x07,0)
        self.dev.UpdateWireIns()
        return
      
    #Historic. The signal still exists but does not fulfil any purpose.
    #Mentioned as 'somereset' in the Verilog file.
    def reset_phs(self):
        
        self.dev.SetWireInValue(0x07,128)
        self.dev.UpdateWireIns()
        time.sleep(1./1000000)
        self.dev.SetWireInValue(0x07,0)
        self.dev.UpdateWireIns()

    def set_clock(self,value = 0):

        #Sets the PLL to use the external or internal clock.
        #0: External Clock // 1: Internal Clock
        if value not in range(2):
            print "Invalid value."
            return       
        self.dev.UpdateWireOuts()
        #The last bit of 0x20 is the activeclock signal.
        self.temp_clock = self.dev.GetWireOutValue(0x20)
        if self.temp_clock < (2**31):
            self.clock = 0
        else:
            self.clock = 1
        if self.clock == value:
            return True
        else:
            self.dev.SetWireInValue(0x07,1)
            self.dev.UpdateWireIns()
            self.dev.SetWireInValue(0x07,0)
            self.dev.UpdateWireIns()
            time.sleep(1./4)
            
        self.dev.UpdateWireOuts()
        self.temp_clock = self.dev.GetWireOutValue(0x20)
        if self.temp_clock < (2**31):
            self.clock = 0
        else:
            self.clock = 1
        if self.clock == value:
            return True
        else:
            #print "There is no external clock connected!"
            return False

    def set_mode(self,mode = 0):

        #mode = 0: random pulses (see mod_rate).
        #mode = 1: pulse pattern defined in pattern memory.
        #For further values cf. set_trg

        self.dev.SetWireInValue(0x00,mode)
        self.dev.UpdateWireIns()

    def set_cable(self,cable,value):
        
        #(de-)activates a wire.
        #cable = wire number (0-158)
        #value == 0 deactivates // value == 1 activates
        self.address = cable / 32
        self.data = 0
        self.select[cable][1] = value

        for i in range(32):
            self.data = self.data + int(self.select[self.address*32 + i][1] * (2**i))

        #Only the first (ouput) word is being written! Must be rewritten if the second word is used.
        self.address = (self.address * 4)
        #print "address:",self.address," data:",hex(self.data)
        self.dev.SetWireInValue(0x02,self.address)
        self.dev.SetWireInValue(0x03,self.data)
        self.dev.UpdateWireIns()
        self.address = self.address + 2
        self.dev.SetWireInValue(0x02,self.address)
        self.dev.UpdateWireIns()
        time.sleep(1./1000000)
        self.address = self.address - 2
        self.dev.SetWireInValue(0x02,self.address)
        self.dev.UpdateWireIns()
        

    def set_modulus(self,mod = 100):
        
        #sets the modulus for the pattern memory.
        #It is not recommended to raise it above the value of the initialisation.
        if mod not in xrange(4096):
            print "Invalid mod value."
            return
        self.dev.SetWireInValue(0x06,mod)
        self.dev.UpdateWireIns()
        
    def set_rate(self,rate = 0x40000000):
    
        #sets the rate parameter for all wires.
        if rate >= 4294967296 or rate < 0:
            print "Invalid rate value."
            return
        self.dev.SetWireInValue(0x01,rate)
        self.dev.UpdateWireIns()

    def set_trg(self,mod = 100,pattern_count_ena = 1, pattern_count = 1):

        #Enables the reaction to trigger_in.
        #pattern_count: amount of patterns sent after a trigger
        #pattern_count_ena: enables pattern_count. If 0, the pattern will run continuously
        #mod: length of the pattern. Maximum is the memory size (4095).
        self.pat = pattern_count*4 + pattern_count_ena*2 + 1
        self.dev.SetWireInValue(0x00,self.pat)
        self.dev.SetWireInValue(0x06,mod)
        self.dev.UpdateWireIns()

    #Only for debugging. Its inherently imprecise.
    def get_cable_out(self,cable):

        #Returns the value of a wire (0/1) at the time of 'UpdateWireOuts()'.
        self.cab = cable/32
        if self.cab == 0:
            self.ep = 0x24
        elif self.cab == 1:
            self.ep = 0x23
        elif self.cab == 2:
            self.ep = 0x22
        elif self.cab == 3:
            self.ep = 0x21
        elif self.cab == 4:
            self.ep = 0x20

        self.mask = 2**(cable % 32)
        self.dev.UpdateWireOuts()
        self.value_temp = self.dev.GetWireOutValue(self.ep)
        self.value = self.mask & self.value_temp
        self.value = self.value / (2**(cable%32))

        return self.value

        #For debugging:
        # if self.value == 1 or self.value == 0:
        #     return self.value
        # else:
        #     print "Invalid value."
        #     return
        

    def set_phshift(self,direction = "up",shift = 1):

        #shifts the phase of the output clock by 'shift' * 0.26 ns 
        #The step width is given by VCO freq = 480 MHz
        #max shift is 127, as determined by the FPGA design.
        #Returns a bool indicating the success.
        if direction == "up":
            self.phasedir = 1
        elif direction == "down":
            self.phasedir = 2
        else:
            print "Invalid value for phase shift 'direction'."
            return False     

        if shift not in xrange(128):
            print shift, "is an invalid amount of steps. Max is 127."
            return False

        # +8 to select counter c0.
        self.phasedata = shift * 512 + self.phasedir * 32 + 8
        self.dev.SetWireInValue(0x07,self.phasedata)
        self.dev.UpdateWireIns()
        #estimated min sleep to guarantee success: 20.3 us (from ModelSim simulation)
        time.sleep(1./10000)
        #Data must be deasserted to reset the counters!
        self.dev.SetWireInValue(0x07,0)
        self.dev.UpdateWireIns()

        for check in range(3):
            self.dev.UpdateWireOuts()
            self.phasedone = self.dev.GetWireOutValue(0x25)
            if self.phasedone >= 2:
                return True
      
        return False


    def write_mem(self,filename):
        
        #writes pattern data stored in appropriate text files.
        #If there is an 'all' option in the text file all other information will be ignored.
        print "\n--- Writing to the pattern memory. ---"
        try:
            self.txt = open(filename)
        except:
            print "Invalid path."
            sys.exit(1)

        print "Memory file: ",filename
        self.allcab = 0
        for eachline in self.txt:
            if "all" in eachline:
                self.allcab = 1
            if self.allcab == 0:
                continue
            if "pattern" in eachline:
                self.char_count = 0
                for char in eachline:
                    if char.isdigit():
                        for cable in range(256):
                            try:
                                self.mem[cable][self.char_count] = int(char)
                            except IndexError:
                                pass
                        self.char_count += 1

        if self.allcab == 0:
               self.cables = []
               self.txt.seek(0)
               for eachline in self.txt:
                   self.tempnr1 = ""
                   if "cable" in eachline:
                       for char in eachline:
                           if char.isdigit():
                               self.tempnr1 += char
                       if self.tempnr1 == "":
                           break
                       self.cable = int(self.tempnr1)
                       self.cables.append(self.cable)
                   if "pattern" in eachline:
                       self.mem_count = 0
                       for char in eachline:
                           if char.isdigit():
                               self.mem[self.cable][self.mem_count] = int(char)
                               self.mem_count += 1

               self.predata = numpy.zeros([8],dtype=numpy.int)
               for entry in self.cables:
                   self.predata[entry/32] += 1

               #predata is used to avoid writing to not changed areas.
               print "cables: ",self.cables
               print "predata: ",self.predata

               for i in range(8):
                   #print "bool: ",self.predata[i] == 0
                   if self.predata[i] == 0:
                       continue
                   for bit in range(self.memsize):
                       self.cd = i*32
                       self.data = 0
                       for k in range(32):
                           self.data = self.data + int(self.mem[self.cd+k][bit] * (2**k))

                       self.address = int(( i + (bit*8)) *2)
                       #print "address: ", hex(address),address,"\ndata: ", hex(data)
                       self.dev.SetWireInValue(0x04,self.address)
                       self.dev.SetWireInValue(0x05,self.data)
                       self.dev.UpdateWireIns()
                       self.address = self.address + 1
                       self.dev.SetWireInValue(0x04,self.address)
                       self.dev.UpdateWireIns()
                       time.sleep(1./1000000)
                       self.dev.SetWireInValue(0x04,self.address - 1)
                       self.dev.UpdateWireIns()

               for entry in self.cables:
                   print "cable: ",entry
                   for i in range(self.memsize):
                       print self.mem[entry][i],
                   print "\n"
               self.txt.close()
               return
        
        for bit in range(self.memsize):
            self.data = 0
            for i in range(32):
                self.data = self.data + int(self.mem[i][bit] * (2**i))
        
            self.dev.SetWireInValue(0x05,self.data)
            for addr in range(8):
                self.address = int(( addr + (bit*8)) *2)
                #print "address: ", hex(address),address,"\ndata: ", hex(data)
                self.dev.SetWireInValue(0x04,self.address)
                self.dev.UpdateWireIns()
                self.address = self.address + 1
                self.dev.SetWireInValue(0x04,self.address)
                self.dev.UpdateWireIns()
                time.sleep(1./1000000)
                self.address = self.address - 1
                self.dev.SetWireInValue(0x04,self.address)
                self.dev.UpdateWireIns()

        print "Pattern written to all cables:"
        for i in range(self.memsize):
            print self.mem[0][i],
        print "\n"
            
        self.txt.close()
        return
