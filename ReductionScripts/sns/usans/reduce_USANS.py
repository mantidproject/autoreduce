#!/usr/bin/env python
import sys,os
import math
import json
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

peaks = []

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

    # Don't load monitors unless we really need them
    #try:
    #    LoadEventNexus(filename, LoadMonitors=True, OutputWorkspace="USANS")
    #    load_monitors = True
    #except:
    #    LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="USANS")
    #    load_monitors = False

    LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="USANS")
    load_monitors = False


    file_prefix = os.path.split(filename)[1].split('.')[0]

    if mtd['USANS'].getRun().hasProperty("BL1A:CS:Scan:USANS:Wavelength"):
        main_wl = mtd['USANS'].getRun().getProperty("BL1A:CS:Scan:USANS:Wavelength").value[0]
    else:
        main_wl = "main_peak"
        
    # Get ROI from logs
    roi_min = mtd['USANS'].getRun().getProperty("BL1A:Det:N1:Det1:TOF:ROI:1:Min").value[0]
    roi_step = mtd['USANS'].getRun().getProperty("BL1A:Det:N1:Det1:TOF:ROI:1:Size").value[0]
    for i in range(1,8):
        lower_bound = mtd['USANS'].getRun().getProperty("BL1A:Det:N1:Det1:TOF:ROI:%s:Min" % i).value[0]
        tof_step = mtd['USANS'].getRun().getProperty("BL1A:Det:N1:Det1:TOF:ROI:%s:Size" % i).value[0]
        
        peaks.append([lower_bound*1000.0, (lower_bound+tof_step)*1000.0])

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
                    mtd["USANS_scan_detector"].setYUnitLabel("Counts")
                    y_data = mtd["USANS_scan_detector"].readY(0)
                    e_data = mtd["USANS_scan_detector"].dataE(0)
                    for i_bin in range(len(y_data)):
                        e_data[i_bin] = math.sqrt(y_data[i_bin])

                    if i == 0:
                        file_path = os.path.join(outdir, "%s_detector_%s.txt" % (file_prefix, main_wl))
                        SaveAscii(InputWorkspace="USANS_scan_detector",Filename=file_path, WriteSpectrumID=False)
                        json_file_path = os.path.join(outdir, "%s_plot_data.json" % file_prefix)
                        SavePlot1DAsJson(InputWorkspace="USANS_scan_detector", JsonFilename=json_file_path, PlotName="main_output")
                        
                        x_data = mtd["USANS_scan_detector"].readX(0)
                        
                        #TODO: add error, which is not part of the scan table
                        x = []
                        y = []
                        e = []
                        for i in range(len(y_data)):
                            x.append(float(x_data[i]))
                            y.append(float(y_data[i]))
                            e.append(float(e_data[i]))
                        if x_min is None or x_min>min(x):
                            x_min = min(x)
                        if x_max is None or x_max<max(x):
                            x_max = max(x)
                        
                        if len(y)>0:
                            # Update json data file for interactive plotting
                            file_path = os.path.join(outdir, "%s_plot_data.dat" % file_prefix)
                            data = {"main_output": {"x":x, "y":y, "e": e, "x_label":short_name, "y_label":"Counts"}}
                            json_data = json.dumps(data)
                            #fd = open(file_path, 'w')
                            #fd.write(json_data)
                            #fd.close()
                    else:
                        file_path = os.path.join(outdir, "%s_detector_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                        SaveAscii(InputWorkspace="USANS_scan_detector",Filename=file_path, WriteSpectrumID=False)
                    
                    CropWorkspace(InputWorkspace="USANS_trans", OutputWorkspace="peak_trans", XMin=peak[0], XMax=peak[1]) 
                    StepScan(InputWorkspace="peak_trans", OutputWorkspace="scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var, ColumnY="Counts", OutputWorkspace="USANS_scan_trans")

                    if i == 0:
                        file_path = os.path.join(outdir, "%s_trans_%s.txt" % (file_prefix, main_wl))
                        SaveAscii(InputWorkspace="USANS_scan_trans",Filename=file_path, WriteSpectrumID=False)
                    else:
                        file_path = os.path.join(outdir, "%s_trans_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                        SaveAscii(InputWorkspace="USANS_scan_trans",Filename=file_path, WriteSpectrumID=False)
                   

    
