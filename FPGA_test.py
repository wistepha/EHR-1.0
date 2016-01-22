import ok,sys,numpy,os,stat,time
from sys import argv
from DTB import DTB,SingleROC

def configureFPGA(dev):

    filename = raw_input("Enter filename or press Enter to use default\n")
    if filename == '':
        filename = "./rbfiles/finalv3_1_top.rbf"

    for i in range(5):
        print "\nConfiguring FPGA...",i+1
        if dev.ConfigureFPGA(filename) != dev.NoError:
            print "Reset unsuccessful."
            return
        else:
            print "FPGA reset successful. File used:", filename
            if dev.IsFrontPanelEnabled():
                print "\n  Initialising wires:"
                print "        pattern_ena = 0"
                dev.SetWireInValue(0x00,0x00000000)
                print "               rate = 2^30"
                dev.SetWireInValue(0x01,0x40000000)
                print "             select = 0"
                dev.SetWireInValue(0x02,0x00000000)
                dev.SetWireInValue(0x03,0x00000000)
                dev.SetWireInValue(0x04,0x00000000)
                dev.SetWireInValue(0x05,0x00000000)
                print "          count_mod = 100"
                dev.SetWireInValue(0x06,0x00000064)
                dev.SetWireInValue(0x07,0x00000000)
                dev.UpdateWireIns()
                print "\n"
                return
            else:
                print "FrontPanel is not enabled."
                time.sleep(1/4.0)
    print "Unsuccessful. Try again."

def bootprofile(dev, devInfo):
    
    # print "This function is not fully implemented, yet..."
    # return

    bootprofile = raw_input("Type in the filename.\n")
    sec = raw_input("Are you sure you want to set",bootprofile,"as the new boot profile? (y/n)")
    if sec == 'n':
        return

    m_devInfo = ok.okTDeviceInfo()

    # if dev.OpenBySerial("") != dev.NoError:
    #     print "Device could not be opened.\nLeaving..."
    #     return
    if (dev.NoError != dev.GetDeviceInfo(devInfo)):
        print ("Error: Unable to retrieve device information.")
        return
    if dev.IsFrontPanelEnabled():
        print "Starting the boot profile reset..."
    else:
        print "FrontPanel is not enabled.\nConsider resetting the FPGA."
        return

    dev.GetDeviceInfo(m_devInfo)
    print "sectorcount and sectorsize:", m_devInfo.flashFPGA.sectorCount,m_devInfo.flashFPGA.sectorSize
    return
    print "Deleting the present boot profile."
    oldprofile
    memset(oldprofile,0,sizeof(okTFPGAResetProfile))
    dev.SetFPGAResetProfile(ok_FPGAConfigurationMethod_NVRAM, oldprofile)

    if m_devInfo.flashFPGA.sectorCount == 0:
        print "This device does not have an appropriate FPGA Flash."
        return
    else:
        print "Available Flash: %d Mib\n", m_devInfo.flashFPGA.sectorCount*m_devInfo.flashFPGA.sectorSize*8/1024/1024


    
def mem_test(dev):

    dev.SetWireInValue(0x00,1)
    dev.UpdateWireIns()

    raw_input("Press enter to end test.")

    dev.SetWireInValue(0x00,0)
    dev.UpdateWireIns()

def mod_mod(dev):
    mod = input("count_mod = ? ")
    dev.SetWireInValue(0x06,mod)
    dev.UpdateWireIns()

def mod_rate(dev):
    
    rate = input("rate = ? ")
    dev.SetWireInValue(0x01,rate)
    dev.UpdateWireIns()

def get_wire(dev):
    
    a = 42
    address = input("Address?")
    dev.UpdateWireOuts()
    a = dev.GetWireOutValue(address)
    print hex(a)

def pat_test(dev):

    try:
        M=SingleROC(rocId=0, dir="/home/stephanwiederkehr/pixel/python/scripts/rocs/test2") 
    except:
        print "DTB exception!"
        return

    tb=DTB(name="DTB_WRQ1WE", module=M)
    tb.SignalProbeD1(DTB.PROBE_PGSYNC)
    tb.SignalProbeD2(DTB.PROBE_CLK)
    tb.mask()
    tb.roc_ClrCal()

    dev.SetWireInValue(0x00,7)
    dev.UpdateWireIns()
    print "------------------------"

    trigger = ''
    while trigger != 'exit':
        trigger = raw_input("Press any key to send a trigger or type 'exit' to leave.")
        if trigger != 'exit':
            #tb.single(DTB.RES)
            tb.adc(7,2)

    switch_clk(dev)
    dev.SetWireInValue(0x00,1)
    dev.UpdateWireIns()

    tb.close()


def mod_cab(dev):
    mod = raw_input("Do you want to turn cables on/off? (y/n)")
    if mod == 'y':
        writing = 'n'
        while writing == 'n':
            address = input("address = ?")
            data = input("data = ?")
            
            address = (address * 4) + 2
            dev.SetWireInValue(0x02,address)
            dev.SetWireInValue(0x03,data)
            dev.UpdateWireIns()

            writing = raw_input("done? (y/n)")

def switch_clk(dev):
    
    value = 0
    leave = raw_input("Press enter to switch clock or exit to leave.")
    if leave == 'exit':
        return
    dev.SetWireInValue(0x07,1)
    dev.UpdateWireIns()
    dev.SetWireInValue(0x07,0)
    dev.UpdateWireIns()

def write_mem(mem,memsize,dev):
    print "--------- Writes data from a file into the memory -------"
    print "---- Use write_mem_file to write a compatible file ------"
    print "Type filename:"
    fil = raw_input("> ")

    try:
        txt = open(fil)
    except:
        print "Invalid file name."
        return

    cables = []

    for eachline in txt:
        tempnr1 = ""
        if "cable" in eachline:
            for char in eachline:
                if char.isdigit():
                    tempnr1 += char
            if tempnr1 == "":
                break
            cable = int(tempnr1)
            cables.append(cable)
        if "pattern" in eachline:
            mem_count = 0
            for char in eachline:
                if char.isdigit():
                    mem[cable][mem_count] = int(char)
                    mem_count += 1

    predata = numpy.zeros([8],dtype=numpy.int)
    for entry in cables:
        predata[entry/32] += 1

    print "cables: ",cables
    print "predata: ",predata

    for i in range(8):
        print "bool: ",predata[i] == 0
        if predata[i] == 0:
            continue
        for bit in range(memsize):
            cd = i*32
            data = 0
            for k in range(32):
                data = data + int(mem[cd+k][bit] * (2**k))

            address = int((( i + (bit*8)) *2) +1)
            #print "address: ", hex(address),address,"\ndata: ", hex(data)
            dev.SetWireInValue(0x04,address)
            dev.SetWireInValue(0x05,data)
            dev.UpdateWireIns()

    for entry in cables:
        print "cable: ",entry
        for i in range(memsize):
            print mem[entry][i],
        print "\n"
    
    txt.close()
def write_mem_all(mem,memsize,dev):

    print "--------- Writes data from a file into the memory -------"
    print "---- Use write_mem_file to write a compatible file ------"
    print "Type filename:"
    fil = raw_input("> ")

    try:
        txt = open(fil)
    except:
        print "Invalid file name."
        return
    
    allcab = 0
    for eachline in txt:
        if "all" in eachline:
            allcab = 1
        if allcab == 0:
            continue
        if "pattern" in eachline:
            mem_count = 0
            for char in eachline:
                if char.isdigit():
                    for cable in range(256):
                        try:
                            mem[cable][mem_count] = int(char)
                        except IndexError:
                            pass
                    mem_count += 1

    for bit in range(memsize):
        data = 0
        for i in range(32):
            data = data + int(mem[i][bit] * (2**i))

        dev.SetWireInValue(0x05,data)
        for addr in range(8):
            address = int((( addr + (bit*8)) *2) +1)
            #print "address: ", hex(address),address,"\ndata: ", hex(data)
            dev.SetWireInValue(0x04,address)
            dev.UpdateWireIns()

    print "Pattern written to all cables:"
    for i in range(memsize):
        print mem[0][i],

    txt.close()

def write_mem_file(memsize):

    memsize = input("Type in pattern length in clock cycles (0 <= length < 4096):\n")

    if memsize not in xrange(4096):
        print "Invalid pattern length. It must be in [0,4095]."
        return

    name = raw_input("Type in the filename:\n")+'.txt'
    overwrite = ''
    try:
        fd = os.open(name, os.O_CREAT|os.O_EXCL|os.O_RDWR)#, stat.S_IREAD|stat.S_IWRITE)
    except OSError:
        overwrite = raw_input("The file already exists. Do you want to overwrite it? (y/n)")
        if overwrite == 'y':
            fd = os.open(name,os.O_RDWR)
        else:
            print "Aborting file creation."
            return
        
    done = 'n'
    while done == 'n':
        cable = raw_input("For which cable do you want to create a pattern?\n")
        try:
            cable = int(cable)
        except ValueError:
            if cable != 'all':
                print "Invalid value. 'cable' must be an integer or 'all'."
                continue
        if cable != 'all':
            if cable > 255 or cable < 0:
                print "Invalid value. Value must be in [0,255]"
                continue
        if cable == 'all':
            os.write(fd,"cables: all;\n")
        else:
            os.write(fd,"cable: %i;\n"%(cable))

        count = 0
        os.write(fd,"pattern: ")
        while count < memsize:
            blocksize = input("Block size? [0,%d] "%(memsize))
            if blocksize < 0 or blocksize > memsize:
                print "Invalid block size. Valid values are in: [0,%d]"%(memsize)
                continue
            value = raw_input("Value? [0,1] ")
            if value != '0' and value != '1':
                print "Invalid value. Valies values are in: [0,1]"
                continue
            for i in range(blocksize):
                if count < memsize:
                    os.write(fd,value)
                    count += 1
        os.write(fd,";\n\n")

        if cable == 'all':
            done = 'y'
            print "Done."
        else:
            done = raw_input("Are you done? (y/n)")
            if done != 'y' and done != 'n':
                done = 'y'
    os.close(fd)

                         


if __name__ == "__main__":

    memsize = 4095
    mem = numpy.zeros([256,memsize],dtype=numpy.int)
    # for i in range(256):
    #     for o in range(memsize):
    #         mem[i][o] = 1

    
    filename = 'finalv3_3.rbf'

    dev = ok.okCFrontPanel()
    devInfo = ok.okTDeviceInfo()

    
    print "\n--------------------------------------------"
    print "    Welcome to the EHR testing program!"
    print "___|"u"\u203e""|___|"u"\u203e""|_|"u"\u203e""|_|"u"\u203e""|_|"u"\u203e""|___|"u"\u203e""|_|"u"\u203e"""u"\u203e"""u"\u203e""|_|"u"\u203e""|____"
    print "--------------------------------------------\n"

    accesserror = 0
    #Commented for debug mode
    if dev.OpenBySerial("") != dev.NoError:
        print "Device could not be opened.\nConsider leaving..."
        accesserror += 1
    if (dev.NoError != dev.GetDeviceInfo(devInfo)):
        print ("Error: Unable to retrieve device information.")
        accesserror += 1
    print("Found Device: " + devInfo.productName)
    print("Device ID: %s" % devInfo.deviceID)
    if dev.IsFrontPanelEnabled():
        print "FrontPanel is enabled."
    else:
        print "FrontPanel is not enabled.\nConsider resetting the FPGA."

    dev.UpdateWireOuts()
    clock = dev.GetWireOutValue(0x20)
    if clock < (2**31):
        print "Clock: External"
    else:
        print "Clock: Internal"

    print "\n  Initialising wires:"
    print "        pattern_ena = 0"
    dev.SetWireInValue(0x00,0x00000000)
    print "               rate = 2^30"
    dev.SetWireInValue(0x01,0x40000000)
    print "             select = 0"
    dev.SetWireInValue(0x02,0x00000000)
    dev.SetWireInValue(0x03,0x00000000)
    dev.SetWireInValue(0x04,0x00000000)
    dev.SetWireInValue(0x05,0x00000000)
    print "          count_mod = 100"
    dev.SetWireInValue(0x06,0x00000064)
    dev.UpdateWireIns()
    print "\n"

    #print dev.GetSerialNumber()

    if accesserror != 0:
        print "The FPGA could not be accessed. Consider one of the following options:"
        print "1. Restart the program."
        print "2. Check the power and USB connection of the device."
        print "3. Check for other programs or computers accessing the device."
        print "4. Reconfigure the FPGA."

    inp = '0'
    while inp != 'exit':
        inp = raw_input("\n----- Awaiting command ----- try 'help'\n")
        if inp == 'help':
            print "Available commands are:  help  mod_cab  reset  write_mem  write_mem_file  write_mem_all  pat_test  mod_rate  mem_test  mod_mod  get_wire exit switch_clk\n"
        elif inp  == 'mod_cab':
            mod_cab(dev)
            print "\n"
        elif inp == 'exit':
            sys.exit()
        elif inp == 'reset':
            configureFPGA(dev)
        elif inp == 'write_mem':
            write_mem(mem,memsize,dev)
        elif inp == 'write_mem_file':
            write_mem_file(memsize)
        elif inp == 'mem':
            print mem
        elif inp == 'pat_test':
            pat_test(dev)
        elif inp == 'mem_test':
            mem_test(dev)
        elif inp == 'mod_rate':
            mod_rate(dev)
        elif inp == 'mod_mod':
            mod_mod(dev)
        elif inp == 'write_mem_all':
            write_mem_all(mem,memsize,dev)
        elif inp == 'switch_clk':
            switch_clk(dev)
        elif inp == 'get_wire':
            get_wire(dev)
        else:
            print "Unknown command: ",inp
 

    

    #raw_input("Waiting for input to close.")
    

    
