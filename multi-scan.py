from DTB import DTB,SingleROC
from ROOT import TGraph, TGraphErrors, TAttAxis, gStyle, TH2F,gPad, TFile, TCanvas, TH1F, TText, TPaveLabel, TPaveText
from FPGA import ZEM
import numpy,array,sys,time,param,random,functions,os

########################################################################

def geteff(histo,trgmax):
    
    content = 0
    for row in range(80):
        for col in range(52):
            content += histo.GetBinContent(col,row)

    tottrg = 52*80*trgmax

    return float(content)/tottrg

if __name__ == "__main__":

    try:
        fd2 = os.open("multi-scan-log.txt", os.O_CREAT|os.O_EXCL|os.O_RDWR)
    except OSError:
        os.remove("multi-scan-log.txt")
        fd2 = os.open("multi-scan-log.txt", os.O_CREAT|os.O_RDWR)
        
    os.write(fd2,"Welcome to the log file for the multi-scan!\n\n")

    #Initialisation of the ROC and programming the TB outputs
    M=SingleROC(rocId=0, dir="/home/wistepha/pixel/pxar/wistepha/roc") 
    tb=DTB(name="DTB_WRQ1WE", module=M)
    tb.SignalProbeD1(DTB.PROBE_PGSYNC)
    tb.SignalProbeD2(DTB.PROBE_CLK)
    tb.mask()
    tb.roc_ClrCal()

    for col in range(52):
        tb.roc_Col_Enable( col, True )
        for row in range(80):
            tb.roc_Pix_Trim( col, row, 15 )

    zem = ZEM(filename = "./rbfiles/finalv3_1_top.rbf")
    zem.set_rate(2000000)
    zem.set_mode(1)

    print "Scanning for tct."
    tb.arm(20,20)
    wbc = M.roc[0].dacs[254]
    for tct in range(wbc, wbc+10):
        tb.tct = tct
        e = tb.adc(15)
        if len(e)>0:
            print "tct ",tct, e
            break
    os.write(fd2,"The tct scan found the following value: %d"%(tct))

    zem.set_mode(0)

    try:
        fd = os.open("multi-scan-errlog.txt", os.O_CREAT|os.O_EXCL|os.O_RDWR)
    except OSError:
        os.remove("multi-scan-errlog.txt")
        fd = os.open("multi-scan-errlog.txt", os.O_CREAT|os.O_RDWR)

    os.write(fd,"Welcome to the error log file for the multi-scan!\n\n")
    

    #testing for events
    # steps = [555000,1110000,1665000,2220000,2775000,3330000,3885000,4440000,4995000,5550000,6105000,6660000,7215000,7770000,8325000,8880000,9435000,9990000,10545000,11100000,11655000,12210000,12765000,13320000,13875000,14430000,14985000,15540000,16095000,16650000,17205000,17760000,18315000,18870000,19425000,30000000,40000000,50000000,60000000,70000000,80000000,90000000,100000000,200000000,300000000,500000000,1000000000,2000000000,3000000000,4000000000]


    c1 = TCanvas("c1", "Canvas", 1200,900)
    c1.Divide(8,10)#two times historange!
    historange = 40

    effnames = []
    phnames = []
    for i in range(historange):
        effnames.append("eff%d"%(i+1))
        phnames.append("ph%d"%(i+1))
    
    for i in range(historange):
        c1.cd(2*(i+1))
        phnames[i] = TH1F(phnames[i],"Vcal Pulse Height Distribution;Pulse Height [ADC];Occurrence",261,0,261)

        c1.cd(2*i+1)
        effnames[i] = TH2F(effnames[i],"Effieciency Map",52,0,52,80,0,80)
        effnames[i].SetTitle("Map;column;row")
        effnames[i].Draw("colz")
        gStyle.SetOptStat(111)
        c1.Update()
    c1.Update()

    
    print "\n"
    tb.roc_ClrCal()

    starttime = time.asctime()
    steps = [1110000,2220000,3330000,4440000,5550000,6660000,7770000,8880000,11100000,13320000]
    #steps = [6660000,7770000,8880000,11100000,13320000]
    #steps = [7770000,8880000,11100000,13320000]
    #steps = [7770000,13320000]
    rates = [25.9,51.7,77.1,102.2,127.3,152.4,176.9,201.5,249.2,295.8]
    #rates = [152.4,176.9,201.5,249.2,295.8]
    #rates = [176.9,201.5,249.2,295.8]
    #rates = [176.9,295.8]
    trgratecounter = 0
    #trgratelist0 = ["10k","30k","60k","100k"] #10k  , 30003 , 60024 , 100k
    trgratelist0 = ["100k"]
    #trgratelist1 = [4000,1333,666,400]  #4000 , 1333  ,  666   , 400
    trgratelist1 = [400]
    #trgratelist2 = [10400,3600,1740,1050]    #10400, 3600  , 1740  , 1050    
    trgratelist2 = [1050]
    trgmax = 100000 # 100000
    #wbclist = [150] #50,100,150,250
    wbclist = [249]
    os.write(fd2,"\n\nPreparing the run using the following values:\n")
    os.write(fd2,"rate steps (raw values):\n")
    for entry in steps:
        os.write(fd2," %d "%(entry))
    os.write(fd2,"\nrate steps (measured values in MHz/cm2):\n")
    for entry in rates:
        os.write(fd2," %d "%(entry))
    os.write(fd2,"\ntrigger rates (raw values):\n")
    for entry1,entry2 in zip(trgratelist1,trgratelist2):
        os.write(fd2, " %d/%d  "%(entry1,entry2))
    os.write(fd2,"\ntrigger rates (calculated values):\n")
    for entry in trgratelist0:
        os.write(fd2," %s "%(entry))
    os.write(fd2,"\nwbc values:\n")
    for entry in wbclist:
        os.write(fd2," %d "%(entry))
    os.write(fd2,"\n")
    tb.single(DTB.RES)
    histocount = 0
    cdcount = 1
    for trgrate,delay in zip(trgratelist1,trgratelist2):
        print "loop values:",trgrate,delay
        for wbc in wbclist:
            tb.setDAC(254,wbc)
            tb.tct = wbc + 6
            print "wbc = ",M.roc[0].dacs[254]
            for rate in steps:
                os.write(fd,"\nwbc: %d , trgrate: %d , rate %d"%(wbc,trgrate,rate))
                zem.set_rate(rate)
                ana_current_before = tb.getIA()
                dig_current_before = tb.getID()
                for row in xrange(80):

                    if trgrate <= 400:
                        if rate > 6000000:
                            if rate > 8000000:
                                if rate > 13000000:
                                    ranges = [range(5),range(5,11),range(11,16),range(16,22),range(22,27),range(27,32),range(32,37),range(37,42),range(42,47),range(47,52)]
                                else:
                                    ranges = [range(8),range(8,17),range(17,25),range(25,34),range(34,43),range(43,52)]
                            else:
                                ranges = [range(13),range(13,26),range(26,39),range(39,52)]
                        else:
                            ranges = [range(17),range(17,35),range(35,52)]
                    elif trgrate <= 666 and rate > 4000000:
                        ranges = [range(26),range(26,52)]
                    else:
                        ranges = [range(52)]
                        
                    for attempt in range(len(ranges)):
                        tb.roc_ClrCal()
                        tb.single(8)
                        for col in ranges[attempt]:
                            tb.arm(col,row)
                        n=[0]*52
                        triggers = 0
                        tb.single(8)
                        events = tb.adc(7, loopena=1,loopparam=trgrate,loopdelay=delay)
                        for e in enumerate(events):
                            if e[0]>=trgmax:
                                break
                            for roc,c,r,ph in e[1].hits():
                                if r == 80:
                                    os.write(fd,"illegal address: col %d,row %d (event length = %d)\n"%(c,r,len(e)))
                                if r==row:
                                    try:
                                        n[c]+=1
                                        phnames[histocount].Fill(ph)
                                    except:
                                        os.write(fd,"illegal address: col %d,row %d\n"%(c,r)) 
                        if max(enumerate(events))[0] < trgmax:
                            print "There were less triggers (",max(enumerate(events))[0],") than expected(",trgmax,")!"
                        triggers += len(events)
                        for col in ranges[attempt]:
                            effnames[histocount].Fill(col,row,n[col])
                        c1.cd(cdcount)
                        effnames[histocount].Draw("colz")
                        c1.cd(cdcount+1)
                        phnames[histocount].Draw()
                        c1.Update()
                        #print "Triggers in row",row,": ",triggers 

                c1.Update()
                cdcount += 2
                histocount += 1
                
                print "\n"
                print "---------------------------------------------------------"
                print "Results for the rate %d, wbc %d, triggerrate %s:"%(rate,wbc,trgratelist0[trgratecounter])
                print "Current before the measurement:\n","Iana: ",ana_current_before,"\n","Idig: ",dig_current_before
                print "Current after the measurement:\n","Iana: ",tb.getIA(),"\n","Idig: ",tb.getID()
                print "---------------------------------------------------------\n"
                os.write(fd2,"\n\nResults for the rate %d, wbc %d, triggerrate %s:"%(rate,wbc,trgratelist0[trgratecounter]))
                os.write(fd2,"Current before the measurement:\nIana: %d \nIdig: %d"%(ana_current_before,dig_current_before))
                os.write(fd2,"Current after the measurement:\nIana: %d \nIdig: %d"%(tb.getIA(),tb.getID()))

                os.write(fd2,"The following files were created:\nmulti-scan-temp.root : Contains the efficiency canvases and pulse height distributions for each run.\nana-temp.root : Contains the graph showing the efficiency as a function of the rate for each trg rate and wbc value.")

        trgratecounter += 1

    c1.Update()
    print "Test started: ",starttime,"\nTest finished: ",time.asctime()
    os.write(fd,"Test started: %s"%(starttime))
    os.write(fd,"Test finished: %s"%(time.asctime()))
    os.write(fd2,"Test started: %d  and finished: %d"%(starttime,time.asctime()))

    rootfile = TFile("multi-scan-temp.root","RECREATE")
    for i in range(historange): 
        effnames[i].Write()
        phnames[i].Write()
    rootfile.Close()
    print "Canvas saved to multi-scan-temp.root!"



    #Analysis
    c2 = TCanvas("c2", "Canvas", 1200,900)
    c2.Divide(2,2)

    rateerror = []
    efferror = []
    for k in rates:
        rateerror.append(0.66+0.0031*k)
        efferror.append(0.002)

    ananames = []
    for j in range(len(trgratelist1)*len(wbclist)):
        ananames.append("Analysis %d"%(j+1))

    anacount = 0
    for i in enumerate(trgratelist1):
        for ii in enumerate(wbclist):
            analist = []
            for iii in range(len(steps)):
                analist.append(geteff(effnames[anacount],trgmax))
                anacount += 1
            print "efficiency for triggerrate {0} and wbc {1}:".format(trgratelist0[i[0]],ii[1]),analist
            c2.cd(i[0]*len(wbclist)+ii[0]+1)
            #creating TGraphErrors
            ananames[i[0]*len(wbclist)+ii[0]] = TGraphErrors(len(steps),array.array('f',rates),array.array('f',analist),array.array('f',rateerror),array.array('f',efferror))
            #Setting its title
            ananames[i[0]*len(wbclist)+ii[0]].SetTitle("Efficiency for TRG rate {0} and wbc {1};Rate [MHz/cm^2];Efficiency [%]".format(trgratelist0[i[0]],ii[1]))
            x = TAttAxis()
            x = ananames[i[0]*len(wbclist)+ii[0]].GetYaxis()
            x.SetTitleOffset(1.4)
            ananames[i[0]*len(wbclist)+ii[0]].SetMarkerColor( 38 )
            ananames[i[0]*len(wbclist)+ii[0]].SetMarkerStyle( 6 ) 
            ananames[i[0]*len(wbclist)+ii[0]].Draw('ap')
            c2.Update()
    c2.Update()

    rootfile = TFile("ana-temp.root","RECREATE")
    for step in range(len(trgratelist1)*len(wbclist)):
        ananames[step].Write()
    rootfile.Close()
    print "analysis saved to ana-temp.root!"

    raw_input("Waiting for input to close.")
    os.close(fd)
    os.close(fd2)
    tb.Poff()
    tb.usb.flush()
    sys.exit()
