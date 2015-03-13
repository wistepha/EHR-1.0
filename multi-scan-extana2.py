from ROOT import TGraph, TGraphErrors, TAttAxis, gStyle, TH2F,gPad, TFile, TCanvas, TH1F, TText, TPaveLabel, TPaveText
import numpy,array,sys,time,param,random,functions,os


def geteff(histo,trgmax):
    
    content = 0
    for row in range(1,81):
        for col in range(1,53):
            content += histo.GetBinContent(col,row)

    tottrg = 52*80*trgmax

    return float(content)/tottrg

if __name__ == "__main__":


    c2 = TCanvas("c2", "Canvas", 1200,900)
    c2.Divide(2,3)

    #Data from the run to be analysed
    fil = TFile("multi-scan-run3.root")
    trgratelist1 = [6666,4000,1333,666,400]
    trgratelist0 = ["bla","10k","30k","60k","100k"]
    wbclist = [249]
    steps = [1110000,2220000,3330000,4440000,5550000,6660000,7770000,8880000,11100000,13320000]
    rates = [25.9,51.7,77.1,102.2,127.3,152.4,176.9,201.5,249.2,295.8]
    historange = 40
    trgmax = 100000


    effnames = []
    for i in range(historange):
        effnames.append("eff%d"%(i+1))
    for name in enumerate(fil.GetListOfKeys()):
        if name[0]%2==0:
            effnames[name[0]/2] = fil.Get(name[1].GetName())
            #print fil.Get(name[1].GetName())
    #print effnames


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
                filchange = raw_input("Proceed or change file?(any/c)")
                
                if filchange == 'c':
                    fil.Close()
                    filname = raw_input("Input filename.")
                    fil = TFile(filname)
                    effnames = []
                    for new in range(historange):
                        effnames.append("eff%d"%(new+1))
                    for name in enumerate(fil.GetListOfKeys()):
                        if name[0]%2==0:
                            effnames[name[0]/2] = fil.Get(name[1].GetName())
                    anacount = 0

                analist.append(geteff(effnames[anacount],trgmax))
                anacount += 1
            #print analist
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


    raw_input("Wait for input to close.")
    rootfile = TFile("anaext-temp.root","RECREATE")
    for step in range(len(trgratelist1)*len(wbclist)):
        ananames[step].Write()
    rootfile.Close()
    print "Saved as anaext-temp.root!"
    fil.Close()
