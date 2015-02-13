#An accumulation of functions
from ROOT import TGraph, gStyle, TH2F,gPad, TFile, TCanvas, TH1F
import numpy,array,sys,time,param,random

#Reads the values from the PHCalibrationFit file and gives out two arrays containing the slope and offset.

def PHClist():
    txt1 = open("/home/wistepha/pixel/python/scripts/oldpyxardata/phCalibrationFit_C0.dat")
    txt = txt1.readlines()
    #list_of_pixels = txt.split("\n")
    txt = txt[3:]

    #dataA: slope and dataB: offset
    dataA = numpy.zeros([52,80])
    dataB = numpy.zeros([52,80])

    for pixel in txt:
	fields = pixel.split()
	col = int(fields[7])
	row = int(fields[8])
	slope = float(fields[2])
	offset = float(fields[3])
        dataA[col][row] = slope
        dataB[col][row] = offset

    return dataA,dataB


#takes the first 9 values from ph calibration (pixel 0 0) and plots them 
#(to make a fit in root)
def PHolist():
    txt1 = open("/home/stephanwiederkehr/pixel/pyxar/data/wistepha/PHCalibration/phCalibration_C0.dat")
    txt = txt1.readlines()
    txt = txt[4:]
    c1 = TCanvas("c1", "Canvas", 1000, 500)
    p = TH1F("b","histo", 1500,0,1500)
    p.Draw()
    p.SetTitle("phCal;Vcal;ph")
    n=[50,100,150,200,250,210,350,490,630,1400]
    for line in txt:
        fields = line.split()
        for i in range(10):
            ph = float(fields[i])
            p.Fill(n[i],ph)
            p.Draw()
        break
    c1.Update()
    rootfile = TFile( "PHolist.root" ,"RECREATE" )
    p.Write()
    rootfile.Close()

    return 

#reads the data from a SCurve_C0_xx.dat file and gives back the values and errors (as fields)                   
def SCurveData():
    Vthr = raw_input("Data for VthrComp = ?")
    try:
        txt1 = open("/home/stephanwiederkehr/pixel/pyxar/data/wistepha/SCurves/SCurve_C0_%s.dat"%(Vthr))
    except IOError:
        print "There is yet no file for such a Vthr!"
        sys.exit()
    txt = txt1.readlines()
    txt = txt[2:]

    #dataA: slope and dataB: offset
    SCFit = numpy.zeros([52,80])
    SCFitError = numpy.zeros([52,80])

    for pixel in txt:
	fields = pixel.split()
	col = int(fields[3])
	row = int(fields[4])
	fit = float(fields[0])
	error = float(fields[1])
        SCFit[col][row] = fit
        SCFitError[col][row] = error

    return SCFit,SCFitError

#Finds a file "name".
def findfile(name,path="/home/stephanwiederkehr/"):
   result = []
   for root,dirs,files in os.walk(path):
      if name in files:
         result.append(os.path.join(root,name))
   if not result:
      print "No match"
   else:
      print "All matches:\n",result
   return None
