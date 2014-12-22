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

def _create_ascii_clicked(first_run_of_set):
    #get default output file name
    default_file_name = 'REFL_' + runNumber + '_combined_data.txt'

    dq0 = 0.0009
    dq_over_q = 0.045
    line1 = '#dQ0[1/Angstrom]=' + str(dq0)
    line2 = '#dQ/Q=' + str(dq_over_q)
    line3 = '#Q(1/Angstrom) R delta_R Precision'
    text = [line1, line2, line3]

    #using mean or value with less error
    wks_file_name = _produce_y_of_same_x_(first_run_of_set)

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

def _produce_y_of_same_x_(first_run_of_set):
    """
    2 y values sharing the same x-axis will be average using
    the weighted mean
    """
    from numpy import NAN
    isUsingLessErrorValue = True
    n_points = 0
    for f in os.listdir(outputDir):
        if f.startswith("REFL_%s" % first_run_of_set) and f.endswith("auto.nxs") and not f.endswith("%s_auto.nxs"%runNumber):
            LoadNexus(Filename=os.path.join(outputDir, f), OutputWorkspace="reflectivity_%sts" % n_points)
            n_points += 1

    ws_list = AnalysisDataService.getObjectNames()
    scaled_ws_list = []

    # Get the list of scaled histos
    for ws in ws_list:
        if ws.endswith("ts"):
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
    first_run_of_set = m.group(1)
    sequence_number = m.group(2)
except:
    pass

reduction_settings = {1: {"signal": [153, 164], "background": [150, 167]},
                      2: {"signal": [153, 164], "background": [150, 167]},
                      3: {"signal": [153, 164], "background": [150, 167]},
                      4: {"signal": [153, 164], "background": [150, 167]},
                      5: {"signal": [153, 164], "background": [150, 167]},
                      6: {"signal": [153, 164], "background": [150, 167]},
                      7: {"signal": [153, 164], "background": [150, 167]}
}

if sequence_number not in reduction_settings:
    sequence_number = 1

RefLReduction(RunNumbers=[int(runNumber)],
              NormalizationRunNumber=119688,
              SignalPeakPixelRange=reduction_settings[sequence_number]["signal"],
              SubtractSignalBackground=True,
              SignalBackgroundPixelRange=reduction_settings[sequence_number]["background"],
              NormFlag=True,
              NormPeakPixelRange=[152, 163],
              NormBackgroundPixelRange=[149, 167],
              SubtractNormBackground=True,
              LowResDataAxisPixelRangeFlag=True,
              LowResDataAxisPixelRange=[98, 158],
              LowResNormAxisPixelRangeFlag=True,
              LowResNormAxisPixelRange=[98, 158],
              TOFRange=[50407.0, 62821.0],
              IncidentMediumSelected='2InDiamSi',
              GeometryCorrectionFlag=False,
              QMin=0.005,
              QStep=0.01,
              AngleOffset=0.009,
              AngleOffsetError=0.001,
              ScalingFactorFile='/SNS/REF_L/IPTS-11601/shared/directBeamDatabaseFall2014_after_16DEC.cfg',
              SlitsWidthFlag=True,
              OutputWorkspace='reflectivity_%s' % runNumber)

n_ts = 0
output_ws = None
for ws in AnalysisDataService.getObjectNames():
    if ws.endswith("ts"):
        output_ws = ws
        n_ts += 1
if n_ts>1:
    print "ERROR: more than one reduced output"

SaveNexus(Filename=os.path.join(outputDir,"REFL_%s_%s_%s_auto.nxs" % (first_run_of_set, sequence_number, runNumber)), InputWorkspace=output_ws)
_create_ascii_clicked(first_run_of_set)

