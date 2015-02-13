import sys,os

#Creates a text file suitable for wire patterns used in FPGA.py

if __name__ == "__main__":

    while True:
        memsize = input("Type in pattern length in clock cycles (0 <= length < 4096):\n")
        if memsize not in xrange(4096):
            print "Invalid pattern length. It must be in [0,4095]. Try again.\n"
        else:
            break
        
    while True:
        name = raw_input("Type in the filename:\n")+'.txt'
        overwrite = ''
        try:
            fd = os.open(name, os.O_CREAT|os.O_EXCL|os.O_RDWR)#, stat.S_IREAD|stat.S_IWRITE)
            break
        except OSError:
            overwrite = raw_input("The file already exists. Do you want to overwrite it? (y/n)")
            if overwrite == 'y':
                os.remove("./%s"%(name))
                fd = os.open(name, os.O_CREAT|os.O_RDWR)
                break
            else:
                print "Try again.\n"
                
    done = 'n'
    while done == 'n':
        cable = raw_input("For which cable do you want to create a pattern (cable-nr. or all)?\n")
        try:
            cable = int(cable)
        except ValueError:
            if cable != 'all':
                print "Invalid value. 'cable' must be an integer or 'all'."
                continue
        if cable != 'all':
            if cable > 158 or cable < 0:
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
            if done != 'n':
                done = 'y'
                print "Done."
    os.close(fd)
