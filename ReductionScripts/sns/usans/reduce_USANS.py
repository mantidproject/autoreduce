#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
from numpy import *
numpy.seterr(all='ignore')

import warnings
warnings.filterwarnings('ignore',module='numpy')

if __name__ == "__main__":    
    #check number of arguments
    if (len(sys.argv) != 3): 
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
        filename = sys.argv[1]
        outdir = sys.argv[2]

    try:
        LoadEventNexus(filename, LoadMonitors=True, OutputWorkspace="USANS")
        load_monitors = True
    except:
        LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="USANS")
        load_monitors = False
    w=mtd["USANS"]
    file_prefix = os.path.split(filename)[1].split('.')[0]

    # Find whether we have a motor turning
    scan_var = None
    for item in mtd['USANS'].getRun().getProperties():
        if item.name.startswith("BL1A:Mot:") and not item.name.endswith(".RBV"):
            stats = item.getStatistics()
            if stats.mean>0 and stats.standard_deviation/item.getStatistics().mean>0.01:
                print item.name
                scan_var = item.name
            
    StepScan(InputWorkspace="USANS_detector", OutputWorkspace="scan_table")
    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var, ColumnY="Counts", OutputWorkspace="USANS_scan_detector")

    StepScan(InputWorkspace="USANS_trans", OutputWorkspace="scan_table")
    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var, ColumnY="Counts", OutputWorkspace="USANS_scan_trans")

    # Produce ASCII data
    Rebin(InputWorkspace="USANS", Params="0,10,17000", OutputWorkspace="USANS")
    SumSpectra(InputWorkspace="USANS",OutputWorkspace="summed")
    file_path = os.path.join(outdir, "%s_detector_trans.txt" % file_prefix)
    SaveAscii(InputWorkspace="summed",Filename=file_path, WriteSpectrumID=False)

    CropWorkspace(InputWorkspace="USANS", StartWorkspaceIndex=0, EndWorkspaceIndex=1023, OutputWorkspace="USANS_detector")
    SumSpectra(InputWorkspace="USANS_detector",OutputWorkspace="summed")
    file_path = os.path.join(outdir, "%s_detector.txt" % file_prefix)
    SaveAscii(InputWorkspace="summed",Filename=file_path, WriteSpectrumID=False)

    CropWorkspace(InputWorkspace="USANS", StartWorkspaceIndex=1024, EndWorkspaceIndex=2047, OutputWorkspace="USANS_trans")
    SumSpectra(InputWorkspace="USANS_trans",OutputWorkspace="summed")
    file_path = os.path.join(outdir, "%s_trans.txt" % file_prefix)
    SaveAscii(InputWorkspace="summed",Filename=file_path, WriteSpectrumID=False)

    if load_monitors:
        Rebin(InputWorkspace="USANS_monitors", Params="0,10,17000", OutputWorkspace="USANS_monitors")
        file_path = os.path.join(outdir, "%s_monitor.txt" % file_prefix)
        SaveAscii(InputWorkspace="USANS_monitors",Filename=file_path, WriteSpectrumID=False)

    wi=Integration(w)
    data=wi.extractY().reshape(16,128)
    data2=data[[4,0,5,1,6,2,7,3, 12,8,13,9,14,10,15,11]]
    X,Y=meshgrid(arange(17), arange(129))
    Z=ma.masked_where(data2<.1,data2)
    pcolormesh(X,Y,log(Z.transpose()))
    ylim([0,128])
    xlim([0,16])
    xlabel('Tube')
    ylabel('Pixel')
    

    image_file = "%s_autoreduced.png" % file_prefix
    image_path = os.path.join(outdir, image_file)
    savefig(str(image_path),bbox_inches='tight')
