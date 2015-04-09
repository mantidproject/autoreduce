#!/usr/bin/env python
import sys,os,math
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")

sys.path.append("/opt/Mantid/bin")
import numpy
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *

import sys
import os
import re
import math
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
import matplotlib
matplotlib.use('agg', warn=False)
import matplotlib.pyplot as plt

if (os.environ.has_key("MANTIDPATH")):
    del os.environ["MANTIDPATH"]
sys.path.insert(0,'/opt/mantidnightly/bin')

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[2]

import mantid
from mantid.simpleapi import *

from LargeScaleStructures.data_stitching import DataSet, Stitcher

sys.path.append("/opt/mantidnightly/scripts/Interface/")
sys.path.append("/SNS/REF_L/shared/autoreduce/")
from reduction_gui.reduction.reflectometer.refl_data_series import DataSeries
from reduce_REF_L_utilities import autoreduction_stitching

def save_partial_output(endswith='auto'):
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

    is_absolute = autoreduction_stitching(outputDir, first_run_of_set, endswith)

    default_file_name = 'REFL_%s_combined_data.txt' % first_run_of_set
    new_file_name = 'REFL_%s_combined_data_%s.txt' % (first_run_of_set, endswith)
    os.system("cp %s %s" % (os.path.join(outputDir, default_file_name),
                            os.path.join(outputDir, new_file_name)))

    return is_absolute

# Load meta data to decide what to do
meta_data = LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=True)
meta_data_run = meta_data.getRun()
first_run_of_set = int(runNumber)
sequence_number = 1
title = meta_data_run.getProperty("run_title").value
try:
    m=re.search("Run:(\d+)-(\d+).",title)
    if m is not None:
        first_run_of_set = m.group(1)
        sequence_number = int(m.group(2))
    else:
        m=re.search("-(\d+).",title)
        if m is not None:
            sequence_number = int(m.group(1))
            first_run_of_set = int(runNumber)-int(sequence_number)-1
        else:
            sequence_number = 1
            first_run_of_set = int(runNumber)
except:
    sequence_number = 1
    first_run_of_set = int(runNumber)

s = DataSeries()
fd = open("/SNS/REF_L/shared/autoreduce/template.xml", "r")
xml_str = fd.read()
s.from_xml(xml_str)

if len(s.data_sets)>sequence_number:
    data_set = s.data_sets[sequence_number-1]
elif len(s.data_sets)>0:
    data_set = s.data_sets[0]
else:
    raise RuntimeError, "Invalid reduction template"

_incident_medium_str = str(data_set.incident_medium_list[0])
_list = _incident_medium_str.split(',')

# Set the following to True to compare the old and new reduction algorithms
compare = False
if compare:
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
                  TofRangeFlag=True,
                  IncidentMediumSelected=_list[data_set.incident_medium_index_selected],
                  GeometryCorrectionFlag=False,
                  QMin=data_set.q_min,
                  QStep=data_set.q_step,
                  AngleOffset=data_set.angle_offset,
                  AngleOffsetError=data_set.angle_offset_error,
                  ScalingFactorFile=str(data_set.scaling_factor_file),
                  SlitsWidthFlag=False, #data_set.slits_width_flag,
                  OutputWorkspace='reflectivity_%s_%s_%s' % (first_run_of_set, sequence_number, runNumber))

    save_partial_output(endswith='new')

    for item in AnalysisDataService.getObjectNames():
        if not item == "reflectivity_new":
            AnalysisDataService.remove(item)
    if AnalysisDataService.doesExist('reflectivity_new'):
        RenameWorkspace(InputWorkspace="reflectivity_new", OutputWorkspace="output_new")

logger.notice("BEFORE "+str(AnalysisDataService.getObjectNames()))
RefLReduction(RunNumbers=[int(runNumber)],
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
              TofRangeFlag=True,
              IncidentMediumSelected=_list[data_set.incident_medium_index_selected],
              GeometryCorrectionFlag=False,
              QMin=data_set.q_min,
              QStep=data_set.q_step,
              AngleOffset=data_set.angle_offset,
              AngleOffsetError=data_set.angle_offset_error,
              ScalingFactorFile=str(data_set.scaling_factor_file),
              SlitsWidthFlag=data_set.slits_width_flag,
              OutputWorkspace='reflectivity_%s_%s_%s' % (first_run_of_set, sequence_number, runNumber))

is_absolute = save_partial_output(endswith='auto')
if AnalysisDataService.doesExist('reflectivity_auto'):
    RenameWorkspace(InputWorkspace="reflectivity_auto", OutputWorkspace="output_auto")

logger.notice(str(AnalysisDataService.getObjectNames()))
# Clean up the output and produce a nice plot for the web monitor
result_list = ['output_auto']
if compare:
    result_list.append('output_new')

group_ws = []
plot_data = []
for item in result_list:
    if not AnalysisDataService.doesExist(item):
        continue
    x_data = mtd[item].dataX(0)
    y_data = mtd[item].dataY(0)
    e_data = mtd[item].dataE(0)
    clean_x = []
    clean_y = []
    clean_e = []
    for i in range(len(y_data)):
        if y_data[i]>0:
            clean_y.append(math.log(y_data[i]))
            clean_x.append(x_data[i])
            clean_e.append(e_data[i])
    CreateWorkspace(DataX=clean_x, DataY=clean_y, DataE=clean_e, NSpec=1,
                    OutputWorkspace=item, UnitX="MomentumTransfer")
    group_ws.append(item)       
    plot_data.append([item, clean_x, clean_y])

y_label = "Reflectivity "
if is_absolute:
    y_label += "(absolute)"
else:
    y_label += "(stitched)"
    
if len(plot_data)>1: 

    plt.cla()
    if len(plot_data)==2:
        plt.plot(plot_data[0][1], plot_data[0][2], '-', plot_data[1][1], plot_data[1][2])
    plt.title(y_label)
    plt.xlabel('Q')
    plt.ylabel('Reflectivity')
    plt.legend([plot_data[0][0], plot_data[1][0]])
    plt.savefig(os.path.join(outputDir,"REF_L_"+runNumber+'.png'))


elif len(group_ws) > 0:
    wsGroup=GroupWorkspaces(InputWorkspaces=group_ws)
    SavePlot1D(InputWorkspace=wsGroup, OutputFilename=os.path.join(outputDir,"REF_L_"+runNumber+'.png'), YLabel=y_label)
else:
    logger.notice("Nothing to plot")
