import sys
import os
import re
import math
import time
import json
import platform
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from matplotlib import *
use("agg")
import warnings
warnings.filterwarnings('ignore',module='matplotlib')
import matplotlib.pyplot as plt
import numpy
numpy.seterr(all='ignore')

if (os.environ.has_key("MANTIDPATH")):
    del os.environ["MANTIDPATH"]
#sys.path.insert(0,'/opt/Mantid/bin')
sys.path.insert(0,'/opt/mantidnightly/bin')

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[2]

import mantid
from mantid.simpleapi import *


#-------------------------------------
# Reduction options
WL_CUTOFF = 10.0  # Wavelength below which we don't need the absolute normalization
PRIMARY_FRACTION_RANGE = [118, 197] #[121,195] #[82,154]
NORMALIZE_TO_UNITY = True #False #True
#-------------------------------------


sys.path.append("/SNS/REF_L/shared/autoreduce/")
from reduction_gui.reduction.reflectometer.refl_data_series import DataSeries
from reduce_REF_L_utilities import autoreduction_stitching, selection_plots

def save_partial_output(endswith='auto', scale_to_unity=True):
    """
        Stitch and save the full reflectivity curve, or as much as we have at the moment.
    """
    n_ts = 0
    output_ws = None
    for ws in AnalysisDataService.getObjectNames():
        if ws.endswith("ts"):
            output_ws = ws
            n_ts += 1
    if n_ts>1:
        print "ERROR: more than one reduced output"

    file_path = os.path.join(outputDir, "REFL_%s_%s_%s_%s.nxs" % (first_run_of_set, sequence_number, runNumber, endswith))
    SaveNexus(Filename=file_path, InputWorkspace=output_ws)

    file_path = autoreduction_stitching(outputDir, first_run_of_set, endswith, 
                                        scale_to_unity=scale_to_unity, wl_cutoff=WL_CUTOFF)
                                           
    return file_path
    

# Load meta data to decide what to do
meta_data = LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=False)
meta_data_run = meta_data.getRun()
first_run_of_set = int(runNumber)
sequence_number = 1
title = meta_data_run.getProperty("run_title").value
if "direct beam" in title.lower():
    logger.notice("Direct beam run: skip")
    sys.exit(0)

thi = meta_data_run.getProperty('thi').value[0]
tthd = meta_data_run.getProperty('tthd').value[0]
if math.fabs(thi-tthd)<0.001:
    logger.notice("Angle appears to be zero: probably a direct beam run")
    sys.exit(0)
try:
    m=re.search("Run:(\d+)-(\d+)\.",title)
    if m is not None:
        first_run_of_set = m.group(1)
        sequence_number = int(m.group(2))
    else:
        m=re.search("-(\d+)\.",title)
        if m is not None:
            sequence_number = int(m.group(1))
            first_run_of_set = int(runNumber)-int(sequence_number)+1
        else:
            sequence_number = -1
            first_run_of_set = int(runNumber)-int(sequence_number)+1
except:
    sequence_number = -1
    first_run_of_set = int(runNumber)-int(sequence_number)+1

if sequence_number == -1:
    raise RuntimeError, "Could not identify sequence number. Make sure the run title ends with -n where 1 < n < 7"
    
# Save selection plots
selection_plots(meta_data, outputDir, runNumber)

# Read in the configuration for this run in the set
# If there is a local template.xml, use it
s = DataSeries()
if os.path.isfile("template.xml"):
    fd = open("template.xml", "r")
else:
    fd = open("/SNS/REF_L/shared/autoreduce/template.xml", "r")
xml_str = fd.read()
s.from_xml(xml_str)

if len(s.data_sets)>=sequence_number:
    data_set = s.data_sets[sequence_number-1]
elif len(s.data_sets)>0:
    data_set = s.data_sets[0]
else:
    raise RuntimeError, "Invalid reduction template"

# Write out a template for this run
xml_str = "<Reduction>\n"
xml_str += "  <instrument_name>REFL</instrument_name>\n"
xml_str += "  <timestamp>%s</timestamp>\n" % time.ctime()
xml_str += "  <python_version>%s</python_version>\n" % sys.version
xml_str += "  <platform>%s</platform>\n" % platform.system()
xml_str += "  <architecture>%s</architecture>\n" % str(platform.architecture())
xml_str += "  <mantid_version>%s</mantid_version>\n" % mantid.__version__

new_data_sets = []
for i in range(int(runNumber)-int(first_run_of_set)+1):
    if i>len(s.data_sets):
        break
    d = s.data_sets[i]
    d.data_files=[int(first_run_of_set)+i]
    new_data_sets.append(d)
s.data_sets = new_data_sets

xml_str += s.to_xml()
xml_str += "</Reduction>\n"
template_file = open(os.path.join(outputDir, "REF_L_%s_auto_template.xml" % first_run_of_set), 'w')
template_file.write(xml_str)
template_file.close()

_incident_medium_str = str(data_set.incident_medium_list[0])
_list = _incident_medium_str.split(',')

LiquidsReflectometryReduction(RunNumbers=[int(runNumber)],
              NormalizationRunNumber=str(data_set.norm_file),
              SignalPeakPixelRange=data_set.DataPeakPixels,
              SubtractSignalBackground=data_set.DataBackgroundFlag,
              SignalBackgroundPixelRange=data_set.DataBackgroundRoi[:2],
              NormFlag=data_set.NormFlag,
              NormPeakPixelRange=data_set.NormPeakPixels,
              NormBackgroundPixelRange=data_set.NormBackgroundRoi,
              SubtractNormBackground=data_set.NormBackgroundFlag,
              LowResDataAxisPixelRangeFlag=data_set.data_x_range_flag,
              LowResDataAxisPixelRange=data_set.data_x_range,
              LowResNormAxisPixelRangeFlag=data_set.norm_x_range_flag,
              LowResNormAxisPixelRange=data_set.norm_x_range,
              TOFRange=data_set.DataTofRange,
              IncidentMediumSelected=_list[data_set.incident_medium_index_selected],
              GeometryCorrectionFlag=False,
              QMin=data_set.q_min,
              QStep=data_set.q_step,
              AngleOffset=data_set.angle_offset,
              AngleOffsetError=data_set.angle_offset_error,
              ScalingFactorFile=str(data_set.scaling_factor_file),
              SlitsWidthFlag=data_set.slits_width_flag,
              ApplyPrimaryFraction=True,
              #BackSlitName="S2",
              #PrimaryFractionRange=[121,195],
              PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
              OutputWorkspace='reflectivity_%s_%s_%s' % (first_run_of_set, sequence_number, runNumber))

file_path = save_partial_output(endswith='auto', scale_to_unity=NORMALIZE_TO_UNITY)
if AnalysisDataService.doesExist('reflectivity_auto'):
    RenameWorkspace(InputWorkspace="reflectivity_auto", OutputWorkspace="output_auto")

# Clean up the output and produce a nice plot for the web monitor
item = 'output_auto'

plot_data = []
qmin = 0
qmax = 0.2


Load(Filename=file_path, OutputWorkspace='output_auto')

ReplaceSpecialValues(InputWorkspace=item, OutputWorkspace=item,
                     NaNValue=0.0, NaNError=0.0,
                     InfinityValue=0.0, InfinityError=0.0)    
x_data = mtd[item].dataX(0)
y_data = mtd[item].dataY(0)
e_data = mtd[item].dataE(0)
clean_x = []
clean_y = []
clean_e = []
qmin = min(x_data)*0.95
qmax = max(x_data)*1.1
for i in range(len(y_data)):
    if y_data[i]>0:
        clean_y.append(y_data[i])
        clean_x.append(x_data[i])
        clean_e.append(e_data[i])
if len(clean_y)>0:
    plot_data.append([item, clean_x, clean_y, clean_e])

# Update json data file for interactive plotting
file_path = os.path.join(outputDir, "REF_L_%s_plot_data.dat" % runNumber)
if os.path.isfile(file_path):
    fd = open(file_path, 'r')
    json_data = fd.read()
    fd.close()
    data = json.loads(json_data)
    data["main_output"] = {"x":clean_x, "y":clean_y, "e": clean_e}
    json_data = json.dumps(data)
    fd = open(file_path, 'w')
    fd.write(json_data)
    fd.close()
  
if len(plot_data)>0: 
    plt.cla()
    plt.plot(plot_data[0][1], plot_data[0][2], '-')
    plt.title('Reflectivity')
    plt.xlabel('Q')
    plt.ylabel('Reflectivity')
    plt.yscale('log')
    plt.xscale('log')
    plt.xlim(xmin=qmin, xmax=qmax)
    plt.ylim(ymax=2.0)
    plt.savefig(os.path.join(outputDir,"REF_L_"+runNumber+'.png'))
else:
    logger.notice("Nothing to plot")

