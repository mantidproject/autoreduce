from __future__ import (absolute_import, division, print_function)
import os
import sys
sys.path.append("/SNS/PG3/shared/autoreduce") # to get csv generation setup
from sumRun_PG3 import addLineToCsv
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid
cal_dir = "/SNS/PG3/shared/CALIBRATION/2017_1_2_11A_CAL/"
cal_file  = os.path.join(cal_dir, 'May2017',
                         'PG3_PAC_d37659_2017_05_24-ALL.h5')
char_backgrounds = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-PAC.txt")
char_bank1 = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-BANK1.txt")
char_bank2 = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-OP.txt")
char_inplane = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-IP.txt")
# grou_bank1 exists as the grouping in the calibration file
group_bank2 = os.path.join(cal_dir, 'Grouping', 'PG3_Grouping-OP.xml')
group_inplane = os.path.join(cal_dir, 'Grouping', 'PG3_Grouping-IP.xml')

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]+'/'

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
ipts = eventFileAbs.split('/')[3]
runNumber = eventFile.split('_')[1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

def clearmem(keepname=None):
    # clear out memory
    def isSpecialName(name):
        return name in ['characterizations', 'PG3_cal', 'PG3_mask']
    names = [name for name in mtd.getObjectNames()
             if not isSpecialName(name)]
    for name in names:
        if keepname is not None and name == keepname:
            continue
        DeleteWorkspace(name)

# first run through is only bank1
SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file,
                   CharacterizationRunsFile=char_backgrounds+','+char_bank1,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0004, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   CacheDir='/tmp',
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

# this will be wrong because it is only bank1
GeneratePythonScript(InputWorkspace="PG3_"+runNumber,
                     Filename=os.path.join(outputDir,"PG3_"+runNumber+'.py'))

clearmem()

# second run through is out-of-plane
SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file,
                   CharacterizationRunsFile=char_backgrounds+','+char_bank2,
                   #OutputFilePrefix='OP_',
                   GroupingFile=group_bank2,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0004, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   CacheDir='/tmp',
                   # don't save gsas here
                   SaveAs="topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

# determine values for SaveGSS
PDDetermineCharacterizations(InputWorkspace='PG3_'+runNumber,
                             Characterizations='characterizations',
                             ReductionProperties="__snspowderreduction")
info = PropertyManagerDataService.retrieve("__snspowderreduction")
# gsas only accepts time-of-flight
ConvertUnits(InputWorkspace='PG3_'+runNumber,
             OutputWorkspace='PG3_'+runNumber,
             Target='TOF',
             EMode='Elastic')
SaveGSS(InputWorkspace='PG3_'+runNumber,
        Filename=os.path.join(outputDir, 'PG3_'+runNumber+'.gsa'),
                              SplitFiles=False, Append=True,
                              MultiplyByBinWidth=(len(info['vanadium'].value) > 0),
                              Bank=info["bank"].value,
                              Format="SLOG", ExtendedHeader=True)

LoadGSS(Filename=os.path.join(outputDir, 'PG3_'+runNumber+'.gsa'),
        OutputWorkspace='PG3_'+runNumber,
        UseBankIDasSpectrumNumber=True)

ConvertUnits(InputWorkspace='PG3_'+runNumber,
             OutputWorkspace='PG3_'+runNumber,
             Target='dSpacing',
             EMode='Elastic')

# interactive plots
try:
    import plotly
    post_image = True
    if post_image:
        div = SavePlot1D(InputWorkspace='PG3_'+runNumber, OutputType='plotly')
        from postprocessing.publish_plot import publish_plot
        request = publish_plot('PG3', runNumber, files={'file':div})
        print("post returned %d" % request.status_code)
        print("resulting document:")
        print(request.text)
    else:
        filename = os.path.join(outputDir, 'PG3_%s.html' % runNumber)
        SavePlot1D(InputWorkspace='PG3_'+runNumber, OutputType='plotly-full',
                   OutputFilename=filename)
        print('saved', filename)
except ImportError:
    pass # don't worry

clearmem()

# third run with only in-plane
SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file,
                   CharacterizationRunsFile=char_backgrounds+','+char_inplane,
                   OutputFilePrefix='IP_',
                   GroupingFile=group_inplane,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0004, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   CacheDir='/tmp',
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

# add the line to the csv file last
addLineToCsv('PG3', eventFileAbs,
             os.path.join(outputDir, 'PG3_%s_runsummary.csv' % ipts))
