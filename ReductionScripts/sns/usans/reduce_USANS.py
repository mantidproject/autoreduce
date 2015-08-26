#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
from numpy import *
numpy.seterr(all='ignore')

import warnings
warnings.filterwarnings('ignore',module='numpy')

peaks = [[10235,12460], [13230,14610], [8825,9450], [6700,7025]]

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
    LoadNexusLogs(Workspace="USANS", Filename=filename, OverwriteLogs=True)
    w=mtd["USANS"]
    file_prefix = os.path.split(filename)[1].split('.')[0]

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

    # Find whether we have a motor turning
    plt.cla()
    twoD = True
    short_name = ''
    plot_data = []
    plot_trans = []
    x_min = None
    x_max = None
    for item in mtd['USANS'].getRun().getProperties():
        if item.name.startswith("BL1A:Mot:") and not item.name.endswith(".RBV"):
            stats = item.getStatistics()
            if abs(stats.mean)>0 and abs(stats.standard_deviation/item.getStatistics().mean)>0.01:
                scan_var = item.name
                short_name = item.name.replace("BL1A:Mot:","")
            
                for i in range(len(peaks)):
                    peak = peaks[i]
                    CropWorkspace(InputWorkspace="USANS_detector", OutputWorkspace="peak_detector", XMin=peak[0], XMax=peak[1])
                    StepScan(InputWorkspace="peak_detector", OutputWorkspace="scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var, ColumnY="Counts", OutputWorkspace="USANS_scan_detector")
                    file_path = os.path.join(outdir, "%s_detector_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                    SaveAscii(InputWorkspace="USANS_scan_detector",Filename=file_path, WriteSpectrumID=False)

                    x_data = mtd["USANS_scan_detector"].readX(0)
                    y_data = mtd["USANS_scan_detector"].readY(0)
                    x = []
                    y = []
                    for item in x_data:
                        x.append(float(item))
                    for item in y_data:
                        y.append(float(item))
                    if x_min is None or x_min>min(x):
                        x_min = min(x)
                    if x_max is None or x_max<max(x):
                        x_max = max(x)
                    
                    plot_data.append([x,y])
                    twoD = False
                    
                    CropWorkspace(InputWorkspace="USANS_trans", OutputWorkspace="peak_trans", XMin=peak[0], XMax=peak[1]) 
                    StepScan(InputWorkspace="peak_trans", OutputWorkspace="scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var, ColumnY="Counts", OutputWorkspace="USANS_scan_trans")
                    file_path = os.path.join(outdir, "%s_trans_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                    SaveAscii(InputWorkspace="USANS_scan_trans",Filename=file_path, WriteSpectrumID=False)

                    x_data = mtd["USANS_scan_trans"].readX(0)
                    y_data = mtd["USANS_scan_trans"].readY(0)
                    x = []
                    y = []
                    for item in x_data:
                        x.append(float(item))
                    for item in y_data:
                        y.append(float(item))
                    if x_min is None or x_min>min(x):
                        x_min = min(x)
                    if x_max is None or x_max<max(x):
                        x_max = max(x)
                    
                    plot_trans.append([x,y])
                   


    image_file = "%s_autoreduced.png" % file_prefix
    image_path = os.path.join(outdir, image_file)
    if twoD==True:
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
        savefig(str(image_path),bbox_inches='tight')
    else:
        plt.cla()
        #plt.plot(plot_data[0][0], plot_data[0][1], '-', plot_data[1][0], plot_data[1][1])
        plt.plot(plot_data[0][0], plot_data[0][1], '-', plot_data[1][0], plot_data[1][1], '-', plot_trans[0][0], plot_trans[0][1], '-', plot_trans[1][0], plot_trans[1][1])
        plt.legend(["Detector Peak 0", "Detector Peak 1", "Trans Peak 0", "Trans Peak 1"])
        plt.title('')
        plt.xlabel(short_name)
        plt.ylabel('')
        plt.yscale('log')
        plt.xlim(xmin=x_min, xmax=x_max)
        plt.savefig(str(image_path))
    
