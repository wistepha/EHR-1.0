from DTB import DTB,SingleROC
from ROOT import TGraph, gStyle, TH2F,gPad, TFile, TCanvas, TH1F, TText, TPaveLabel, TPaveText
from FPGA import ZEM
import numpy,array,sys,time,param,random,functions




########################################################################
if __name__ == "__main__":

    #Initialisation of the ROC and programming the TB outputs
    M=SingleROC(rocId=0, dir="/home/wistepha/pixel/python/scripts/rocs/test2") 
    tb=DTB(name="DTB_WRQ1WE", module=M)
    tb.SignalProbeD1(DTB.PROBE_PGSYNC)
    tb.SignalProbeD2(DTB.PROBE_CLK)
    tb.mask()
    tb.roc_ClrCal()

    #52
    for col in range(52):
        tb.roc_Col_Enable( col, True )
        for row in range(80):
            tb.roc_Pix_Trim( col, row, 15 )

    # tb.roc_Col_Enable(15,True)
    # tb.roc_Pix_Trim(15,27,15)
    
# #To find the wbc for an Vcal. Not needed if no pixel is armed.
    # tb.arm(20,10)
    # lmax=0
    # tctmax=100
    # wbc = M.roc[0].dacs[254]
    # for tct in range(wbc-10,wbc+30):
    #     tb.tct = tct
    #     e = tb.adc(15)
    #     print tct,e
    #     if len(e)>0:
    #         print "tct: ",tct
    #     if len(e)>lmax:
    #         lmax=len(e)
    #         tctmax=tct

    # sys.exit()
    
    # tb.tct = tctmax
    # print 'tctmax = ',tctmax

    zem = ZEM(filename = "./rbfiles/phshift3.rbf")
    #rate = 19425000
    rate = 2000000000
    zem.set_rate(rate)
    # #zem.set_rate(0x00200000)
    zem.set_mode(0)

    for cable in range(159):
        zem.set_cable(cable,0)

    zem.set_cable(1,1)

    #tb.deser160()

    #ntrig = param.trigadc*param.nloop
    c1 = TCanvas("c1", "Canvas", 300,0,900, 1000)
    c1.Divide(1,4)

    c1.cd(1)
    h = TH2F("a","Map",52, 0., 52., 80, 0., 80)
    gStyle.SetOptStat(111)
    h.Draw("colz")
    tb.roc_ClrCal()
    h.SetTitle("Map;column;row")
    
    c1.cd(2)
    p = TH1F("b","event distribution", 120,0,120)
    p.Draw()
    #Title is set again in the end, containing trigger and rate information.
    #p.SetTitle("event distribution for %d triggers;#hits/event;occurrence"%(ntrig))

    c1.cd(3)
    l = TH1F("c","events per loop distribution", param.trigadc/4,0,param.trigadc/4)
    l.Draw()
    l.SetTitle("events per loop distribution;events per loop;occurrence")

    c1.cd(4)
    o = TH1F("d", "pulse height per hit", 800,0,800)
    o.Draw()
    o.SetTitle("ph per hit;pulse height[Vcal];occurrence")
    
    print "\n"

    print "Current before the measurement:\n","Iana: ",tb.getIA(),"\n","Idig: ",tb.getID()

    #print tb.adc(15)
    #tb.setDAC(12,60)
    #el = events per loop
    dataA,dataB = functions.PHClist()
    starttime = time.asctime()
    yy = numpy.zeros([3,param.iloop])
    for i in range(param.iloop):
        tb.single(DTB.RES)
        nhit=0
        trigs = 0
        for n in range(param.nloop):
            el = 0
            #if param.showres == 0:
            #    print n
            #tb.arm (20,20)
            events = tb.adc(7, param.trigadc,loopena = 1,loopparam = 4000,loopdelay = 10500) 
            trigs += len(events)
            #print "!!!",len(events),max([len(e) for e in events])
            #print len(events)
            #time.sleep(random.randint(1,10)/10)
            for e in events:
                for roc, c,r, ph in e.hits():
                    #if (0 > c or c > 51) or (0 > r or r > 79):
                        #print "Illegal value:","c =",c,"r =",r,"len(e) =",len(e)
                    h.Fill(c,r,1)
                    try:
                        #o.Fill((ph-dataB[c][r])/dataA[c][r])
                        o.Fill(ph)
                    except IndexError:
                        print "illegal address ",c,r
                    #print c,r,ph,(ph-dataB[c][r])/dataA[c][r]
                    #print (ph-dataB[c][r])/dataA[c][r] 
                nhit+=len(e)
                if len(e)>0:
                    #print "hits: ",len(e)
                    el += 1
                    p.Fill(len(e))
            l.Fill(el)
            #print el

            c1.cd(1)
            h.Draw("colz")
            c1.cd(2)
            p.Draw()
            c1.cd(3)
            l.Draw()
            c1.cd(4)
            o.Draw()
            c1.Update()

        ntrig = param.trigadc*param.nloop   
        if param.showres == 0:
            print "results of exp. nr. ",i+1,":"
            print "triggers: ",trigs
            print "hits: ",nhit
            print "non zero events: ",el," (expected",float(rate*trigs)/(2**32 - 1),")"
            if el != 0:
                print "non zeros per total events: ",float(el)/trigs
                print "mean hits per non zero event: ",float(nhit)/el
            else:
                print "no non zero events found."
            print "rate = ",float(nhit)/trigs," hits/25 ns/ROC "
            print "rate = ",float(nhit)/trigs*40/0.64," MHz/ cm^2 \n"


        p.SetTitle("event distr. for %d triggers and rate %f;#hits/event;occurrence"%(ntrig,float(nhit)/trigs*40/0.64))
        c1.cd(2)
        p.Draw()
        c1.Update()

        #yy contains hit, rate and trigger info for each iloop
        #used to calculate means for all iloops
        yy[0][i] = trigs
        yy[1][i] = nhit
        yy[2][i] = float(nhit)/trigs*40/0.64

    print "Current after the measurement:\n","Iana: ",tb.getIA(),"\n","Idig: ",tb.getID()

    mhits = numpy.mean(yy[1])
    mrate = numpy.mean(yy[2])
    print "\ntotal #triggers: ",numpy.sum(yy[0])
    print "total #hits: ",numpy.sum(yy[1]),"  mean: ",mhits," standard deviation: ",numpy.sqrt(numpy.mean((yy[1]-mhits)**2))
    print "mean rate: ",mrate," standard deviation: ",numpy.sqrt(numpy.mean((yy[2]-mrate)**2))
    print "Test started: ",starttime,"\nTest finished: ",time.asctime()

    #to save plot (not root) as pdf
    #filename="map-"+time.strftime("%Y-%m-%d-%H-%M")+".pdf"
    #gPad.Print("/home/stephanwiederkehr/Desktop/"+filename)

    #feeble attempt to write trigger & rate info into pave text instead of title.
    
    #title = TPaveLabel(0.1,0.94,0.9,0.98,"The title")
    #pave = TPaveText(0.1,0.8,0.9,0.95,"tr")
    #pave.SetFillColor(42)
    #t1 = pave.AddText("here will be the rate")
    #t1.SetTextColor(4)
    #t1.SetTextSize(0.05)
    #pave.AddText("second attempt")
    #pave.Draw()
    #c1.Update

    #to create root file "test.root":
    rootfile = TFile( "test.root" ,"RECREATE" )
    h.Write()
    p.Write()
    l.Write()
    o.Write()
    rootfile.Close()

    if param.ontest > 0:
        sys.exit()
    else:
        raw_input("Waiting for input to close")
    

    tb.Poff()
    tb.usb.flush()
    
