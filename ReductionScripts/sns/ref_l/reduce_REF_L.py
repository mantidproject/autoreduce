# Script automatically generated by Mantid on Wed Feb 15 15:59:58 2012
import sys
import os
import re
import math
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


def _scale_data_sets(workspace_list, endswith='combined'):
    """
        Perform auto-scaling
    """
    s = Stitcher()

    n_data_sets = len(workspace_list)
    for i in range(n_data_sets):
        item = workspace_list[i]
        data = DataSet(item)
        data.load(True, False)

        s.append(data)

    if s.size()==0:
        return

    s.set_reference(0)
    s.compute()

    for i in range(n_data_sets):
        d = s.get_data_set(i)
        xmin, xmax = d.get_skipped_range()
        scale = d.get_scale()
        d.apply_scale(xmin, xmax)

    # Create combined output
    s.get_scaled_data(workspace="reflictivity_%s" % endswith)

def _create_ascii_clicked(first_run_of_set, endswith="auto"):
    #get default output file name
    default_file_name = 'REFL_%s_combined_data.txt' % first_run_of_set

    dq0 = 0.0009
    dq_over_q = 0.045
    line1 = '#dQ0[1/Angstrom]=' + str(dq0)
    line2 = '#dQ/Q=' + str(dq_over_q)
    line3 = '#Q(1/Angstrom) R delta_R Precision'
    text = [line1, line2, line3]

    #using mean or value with less error
    wks_file_name = _produce_y_of_same_x_(first_run_of_set, endswith=endswith)

    x_axis = mtd[wks_file_name].readX(0)[:]
    y_axis = mtd[wks_file_name].readY(0)[:]
    e_axis = mtd[wks_file_name].readE(0)[:]

    sz = len(x_axis)-1
    for i in range(sz):
        # do not display data where R=0
        if (y_axis[i] > 1e-15):
            _line = str(x_axis[i])
            _line += ' ' + str(y_axis[i])
            _line += ' ' + str(e_axis[i])
            _precision = str(dq0 + dq_over_q * x_axis[i])
            _line += ' ' + _precision
            text.append(_line)

    file_path = os.path.join(outputDir, default_file_name)
    print file_path
    f=open(file_path,'w')
    for _line in text:
        f.write(_line + '\n')
    f.close()

def _produce_y_of_same_x_(first_run_of_set, endswith="auto"):
    """
    2 y values sharing the same x-axis will be average using
    the weighted mean
    """
    from numpy import NAN
    isUsingLessErrorValue = True
    n_points = 0
    for f in os.listdir(outputDir):
        if f.startswith("REFL_%s" % first_run_of_set) and f.endswith("%s.nxs" % endswith) and not f.endswith("%s_%s.nxs" % (runNumber, endswith)):
            ws_name = f.replace("_auto.nxs", "")
            ws_name = ws_name.replace("REFL_", "")
            LoadNexus(Filename=os.path.join(outputDir, f), OutputWorkspace="reflectivity_%sts" % ws_name)
            n_points += 1

    ws_list = AnalysisDataService.getObjectNames()
    scaled_ws_list = []
    for ws in ws_list:
        if ws.endswith("ts"):
            scaled_ws_list.append(ws)

    _scale_data_sets(scaled_ws_list, endswith)
    
    ws_list = AnalysisDataService.getObjectNames()
    scaled_ws_list = []
    for ws in ws_list:
        if ws.endswith("scaled"):
            scaled_ws_list.append(ws)

    # get binning parameters
    _from_q = 0.005
    _bin_size = 0.01
    _bin_max = str(2)
    binning_parameters = str(_from_q) + ',-' + str(_bin_size) + ',' + str(_bin_max)

    file_number = 0
    for ws in scaled_ws_list:
        data_y = mtd[ws].dataY(0)
        data_e = mtd[ws].dataE(0)

        # cleanup data 0-> NAN
        for j in range(len(data_y)):
            if data_y[j] < 1e-12:
                data_y[j] = NAN
                data_e[j] = NAN

        file_number = file_number + 1

    # Convert each histo to histograms and rebin to final binning
    for ws in scaled_ws_list:
        new_name = "%s_histo" % ws
        ConvertToHistogram(InputWorkspace=ws, OutputWorkspace=new_name)
        Rebin(InputWorkspace=new_name, Params=binning_parameters,
              OutputWorkspace=new_name)

    # Take the first rebinned histo as our output
    data_y = mtd[scaled_ws_list[0]+'_histo'].dataY(0)
    data_e = mtd[scaled_ws_list[0]+'_histo'].dataE(0)

    # skip first 3 points and last one
    skip_index = 0
    point_to_skip = 3
    # Add in the other histos, averaging the overlaps
    for i in range(1, len(scaled_ws_list)): 
        print  scaled_ws_list[i]
        skip_point = True
        can_skip_last_point = False

        data_y_i = mtd[scaled_ws_list[i]+'_histo'].dataY(0)
        data_e_i = mtd[scaled_ws_list[i]+'_histo'].dataE(0)
        for j in range(len(data_y_i)-1):
            if data_y_i[j] > 0:
                can_skip_last_point = True
                if skip_point:
                    skip_index = skip_index + 1
                    if skip_index == point_to_skip:
                        skip_point = False
                        skip_index = 0
                    else:
                        continue

            if can_skip_last_point and (data_y_i[j+1]==0):
                break

            if data_y[j]>0 and data_y_i[j]>0:
                if isUsingLessErrorValue:
                    if (data_e[j] > data_e_i[j]):
                        data_y[j] = data_y_i[j]
                        data_e[j] = data_e_i[j]
                else:
                    [data_y[j], data_e[j]] = weightedMean([data_y[j], data_y_i[j]], [data_e[j], data_e_i[j]])

            elif (data_y[j] == 0) and (data_y_i[j]>0):
                data_y[j] = data_y_i[j]
                data_e[j] = data_e_i[j]


    return scaled_ws_list[0]+'_histo'

def weightedMean(data_array, error_array):

    sz = len(data_array)

    # calculate the numerator of mean
    dataNum = 0;
    for i in range(sz):
        if not (data_array[i] == 0):
            tmpFactor = float(data_array[i]) / float((pow(error_array[i],2)))
            dataNum += tmpFactor

    # calculate denominator
    dataDen = 0;
    for i in range(sz):
        if not (error_array[i] == 0):
            tmpFactor = 1./float((pow(error_array[i],2)))
            dataDen += tmpFactor

    if dataDen == 0:
        mean = 0
        mean_error = 0
    else:
        mean = float(dataNum) / float(dataDen)
        mean_error = math.sqrt(1/dataDen)

    return [mean, mean_error]



#remove all previous workspaces
list_mt = AnalysisDataService.getObjectNames()
for _mt in list_mt:
    if _mt.find('_scaled') != -1:
        AnalysisDataService.remove(_mt)
    if _mt.find('reflectivity') != -1:
        AnalysisDataService.remove(_mt)

from reduction.command_interface import ReductionSingleton
ReductionSingleton.clean()

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
    data_set = s.data_sets[sequence_number]
elif len(s.data_sets)>0:
    data_set = s.data_sets[0]
else:
    raise RuntimeError, "Invalid reduction template"

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
                  SlitsWidthFlag=data_set.slits_width_flag,
                  OutputWorkspace='reflectivity_%s_%s_%s' % (first_run_of_set, sequence_number, runNumber))

    _create_ascii_clicked(first_run_of_set, "new")

_incident_medium_str = str(data_set.incident_medium_list[0])
_list = _incident_medium_str.split(',')

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

n_ts = 0
output_ws = None
for ws in AnalysisDataService.getObjectNames():
    if ws.endswith("ts"):
        output_ws = ws
        n_ts += 1
if n_ts>1:
    print "ERROR: more than one reduced output"

SaveNexus(Filename=os.path.join(outputDir,"REFL_%s_%s_%s_auto.nxs" % (first_run_of_set, sequence_number, runNumber)), InputWorkspace=output_ws)


#_create_ascii_clicked(first_run_of_set)
from liquids_reflectometry_stitching import autoreduction_stitching
is_absolute = autoreduction_stitching(outputDir, first_run_of_set, "auto")

result_list = ['auto']
if compare:
    result_list.append('new')
group_ws = []
for item in result_list:
    x_data = mtd['reflictivity_%s' % item].dataX(0)
    y_data = mtd['reflictivity_%s' % item].dataY(0)
    e_data = mtd['reflictivity_%s' % item].dataE(0)
    clean_x = []
    clean_y = []
    clean_e = []

    for i in range(len(y_data)):
            if y_data[i]>0:
                clean_y.append(math.log(y_data[i]))
                clean_x.append(x_data[i])
                clean_e.append(e_data[i])
    CreateWorkspace(DataX=clean_x, DataY=clean_y, DataE=clean_e, NSpec=1, OutputWorkspace='reflictivity_%s' % item, UnitX="MomentumTransfer")
    group_ws.append('reflictivity_%s' % item)       

wsGroup=GroupWorkspaces(','.join(group_ws))
y_label = "Reflectivity "
if is_absolute:
    y_label += "(absolute)"
else:
    y_label += "(stitched)"
SavePlot1D(InputWorkspace=wsGroup, OutputFilename=os.path.join(outputDir,"REF_L_"+runNumber+'.png'), YLabel='Intensity')

