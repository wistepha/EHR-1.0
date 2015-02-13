from DTB import DTB,SingleROC
from ROOT import TGraph, gStyle, TH2F,gPad, TFile, TCanvas, TH1F, TText, TPaveLabel, TPaveText
from FPGA import ZEM
import numpy,array,sys,time,param,random,functions,ok


########################################################################
if __name__ == "__main__":

    M=SingleROC(rocId=0, dir="rocs/test2") 
    tb=DTB(name="*", module=M)
    tb.SignalProbeD1(DTB.PROBE_PGSYNC)
    tb.SignalProbeD2(DTB.PROBE_CLK)
    tb.mask()
    tb.roc_ClrCal()

    for col in range(52):
        tb.roc_Col_Enable( col, True )
        for row in range(80):
            tb.roc_Pix_Trim( col, row, 15 )

    zem = ZEM(filename = "./rbfiles/phshift2.rbf")
    #zem = ZEM(filename = "./rbfiles/pllreset.rbf")
    #zem.set_trg()
    #zem.write_mem("tct.txt")
    zem.set_rate(26000000)
    #zem.set_rate(100000000)
    zem.set_mode(0)

    for cable in range(159):
        zem.set_cable(cable,0)

    # for cable in range(40):
    #     zem.set_cable(cable,1)
                      

    # ##fix tct only for testing purposes.
    # #tb.tct = 120

    # print "Scanning for tct."
    # tb.tct = M.roc[0].dacs[254] + 20#100
    # tb.roc_ClrCal()

    # #tct scan
    # lmax=0
    # tctmax=100
    # tb.single(8)
    # wbc = M.roc[0].dacs[254]
    # for tct in range(wbc,wbc+35):
    #     tb.tct = tct
    #     e = tb.adc(7)
    #     print tct,e
    #     #if len(e)>0:
    #         #print "tct: ",tct
    #         #break
    #     if len(e)>lmax:
    #         lmax=len(e)
    #         tctmax=tct
    # tb.tct = tctmax
    # print "tct: ",tctmax

    c2 = TCanvas("c2", "Canvas",1200,900)
    total = TH2F("total","Complete map",52,0,52,80,0,80)
    total.SetTitle("Complete map;column;row")
    total.Draw("colz")
    c2.Update()

    c1 = TCanvas("c1", "Canvas", 1200, 900)
    c1.Divide(10,16)

    names = []
    labels = []
    labeltext = []
    for i in range(159):
        names.append("c%d"%(i))
        labels.append("l%d"%(i))
        labeltext.append("%d"%(i))
    #print "cables:",names
    
    for i in range(159):
        c1.cd(i+1)
        #name = "%d"%(i+1)
        names[i] = TH2F(names[i],"Map",52,0,52,80,0,80)
        names[i].SetTitle("Map;column;row")
        names[i].Draw("colz")
        gStyle.SetOptStat(111)
        c1.Update()
    c1.Update()


    # #Progress bar
    sys.stdout.write("[%s]" %(" "*10))
    sys.stdout.flush()
    sys.stdout.write("\b" * (10+1))
    prbar = 158./10

    error = []
    empty = []

    tb.single(8)
    for cable in range(159):
        zem.set_cable(cable,0)
    time.sleep(1)
    count = 0
    for cable in range(159):
        #print "prior"
        for prior in range(0,cable):
            zem.set_cable(prior,0)
        c1.cd(count+1)
        tb.single(8)
        zem.set_cable(cable,1)
        tb.single(8)
        ep = 0
        for i in range(1000):
            ep += zem.get_cable_out(cable)
        if ep == 0:
            print "cable:",cable,"ep:",ep
        events = tb.adc(7,5000,loop=0)
        errorcheck = 0
        for e in events:
            for roc,c,r,ph in e.hits():
                try:
                    names[count].Fill(c,r,1)
                    total.Fill(c,r,1)
                except:
                    #print "Illegal values c,r: ",c,r
                    error.append(e)
            if len(e) != 0:
                errorcheck = 1
        if errorcheck == 0:
            empty.append(cable)
        # events = tb.adc(7)
        # for roc,c,r,ph in events.hits():
        #     try:
        #         names[count].Fill(c,r,1)
        #     except:
        #         print "Illegal values c,r: ",c,r
        count = count + 1
        while cable >= prbar:
            sys.stdout.write("-")
            sys.stdout.flush()
            prbar += 158./10
        gPad.Update()
    print "\n"
    
    if error != []:
        print "Errors:",error
    if empty != []:
        print "Not active wires:\n",empty
        print "In total:",len(empty),"dead wires."
        
    #hardcode version
    # tb.single(8)
    # data = 2147483648
    # for cable in range(10):
    #     c1.cd(cable+1)
    #     data = (data * 2) % 4294967295
    #     #print hex(data)
    #     zem.dev.SetWireInValue(0x03,data)
    #     addr = (cable / 32) + 2
    #     zem.dev.SetWireInValue(0x02,addr)
    #     zem.dev.UpdateWireIns()
    #     time.sleep(1./1000000)
    #     events = tb.adc(7)
    #     #print events
    #     for roc,c,r,ph in events.hits():
    #         names[cable].Fill(c,r,1)
            
        # for e in events:
        #     for roc,c,r,ph in e.hits():
        #         names[cable].Fill(c,r,1)

    for i in range(159):
        c1.cd(i+1)
        names[i].Draw("colz")
    c1.Update()

    c2.cd()
    for i in range(159):
        xmean = names[i].GetMean(1)
        ymean = names[i].GetMean(2)
        labels[i] = TText(xmean,ymean,labeltext[i])
        labels[i].SetTextColor(1)
        labels[i].SetTextSize(0.02)
        labels[i].Draw()

    gStyle.SetOptStat(0)
    c2.Update()
    tb.Poff()
    tb.usb.flush()
    raw_input("Wait for input to close.")
