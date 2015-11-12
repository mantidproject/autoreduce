#!/usr/bin/env python
import sys,os
import math
import json
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
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
    try:
        LoadEventNexus(filename, LoadMonitors=True, OutputWorkspace="USANS")
        load_monitors = True
    except:
        LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="USANS")
        load_monitors = False

    #LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="USANS")
    #load_monitors = False


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
    short_name = ''
    wavelength=[3.6,1.8,1.2,0.9,0.72,0.6]
    for item in mtd['USANS'].getRun().getProperties():
        if item.name.startswith("BL1A:Mot:") and not item.name.endswith(".RBV"):
            stats = item.getStatistics()
            if abs(stats.mean)>0 and abs(stats.standard_deviation/item.getStatistics().mean)>0.01:
                scan_var = item.name
                short_name = item.name.replace("BL1A:Mot:","")

                y_monitor = None
                if load_monitors:
                    StepScan(InputWorkspace="USANS_monitors", OutputWorkspace="mon_scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="mon_scan_table", ColumnX=scan_var,
                                                  ColumnY="Counts", ColumnE="Error", OutputWorkspace="USANS_scan_monitor")
                    file_path = os.path.join(outdir, "%s_monitor_scan_%s.txt" % (file_prefix, short_name))                
                    SaveAscii(InputWorkspace="USANS_scan_monitor",Filename=file_path, WriteSpectrumID=False)
                    y_monitor = mtd["USANS_scan_monitor"].readY(0)

                iq_file_path = os.path.join(outdir, "%s_iq_%s.txt" % (file_prefix, short_name))
                iq_fd = open(iq_file_path, 'w')
                iq_fd.write("# %8s %10s %10s %10s %10s %10s %5s\n" % ("Q", "I(Q)", "dI(Q)", "dQ", "N(Q)", "dN(Q)", "Lambda"))     
                for i in range(len(peaks)):
                    peak = peaks[i]
                    CropWorkspace(InputWorkspace="USANS_detector", OutputWorkspace="peak_detector", XMin=peak[0], XMax=peak[1])
                    StepScan(InputWorkspace="peak_detector", OutputWorkspace="scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var,
                                                  ColumnY="Counts", ColumnE="Error", OutputWorkspace="USANS_scan_detector")
                    mtd['USANS_scan_detector'].getAxis(1).getUnit().setLabel("Counts", "Counts")
                    y_data = mtd["USANS_scan_detector"].readY(0)
                    e_data = mtd["USANS_scan_detector"].readE(0)

                    if i == 0:
                        file_path = os.path.join(outdir, "%s_detector_%s.txt" % (file_prefix, main_wl))
                        SaveAscii(InputWorkspace="USANS_scan_detector",Filename=file_path, WriteSpectrumID=False)
                        json_file_path = os.path.join(outdir, "%s_plot_data.json" % file_prefix)
                        SavePlot1DAsJson(InputWorkspace="USANS_scan_detector", JsonFilename=json_file_path, PlotName="main_output")
                    else:
                        file_path = os.path.join(outdir, "%s_detector_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                        SaveAscii(InputWorkspace="USANS_scan_detector",Filename=file_path, WriteSpectrumID=False)
                        q_data = []
                        for theta_value in range(len(x_data)):
                            q = 6.28*math.sin(theta_value)/wavelength[i-1]
                            q_data.append(q)
                            
                            # Write I(q) file
                            i_q = y_value[i]
                            iq_fd.write("%-10.6g %-10.6g %-10.6g %-10.6g %-10.6g %-10.6g %-5.4g\n" % (q, i_q, di_q, 0, y_value[i], e_value[i], wavelength[i-1]))
                            
                        
                    
                    CropWorkspace(InputWorkspace="USANS_trans", OutputWorkspace="peak_trans", XMin=peak[0], XMax=peak[1]) 
                    StepScan(InputWorkspace="peak_trans", OutputWorkspace="scan_table")
                    ConvertTableToMatrixWorkspace(InputWorkspace="scan_table", ColumnX=scan_var,
                                                  ColumnY="Counts", OutputWorkspace="USANS_scan_trans")

                    if i == 0:
                        file_path = os.path.join(outdir, "%s_trans_%s.txt" % (file_prefix, main_wl))
                        SaveAscii(InputWorkspace="USANS_scan_trans",Filename=file_path, WriteSpectrumID=False)
                    else:
                        file_path = os.path.join(outdir, "%s_trans_scan_%s_peak_%s.txt" % (file_prefix, short_name, i))
                        SaveAscii(InputWorkspace="USANS_scan_trans",Filename=file_path, WriteSpectrumID=False)
                   
                   
                iq_fd.close()
    
