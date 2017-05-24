import os
import sys
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid
cal_dir = "/SNS/PG3/shared/CALIBRATION/2017_1_2_11A_CAL/"
cal_file  = os.path.join(cal_dir, "PG3_PAC_d37631_2017_05_24.h5")
char_file = os.path.join(cal_dir, "PG3_char_2017_05_20-HR.txt")
#cal_file  = os.path.join(cal_dir, "PG3_MICAS_d36952_2016_11_09.h5")
#char_file = os.path.join(cal_dir, "PG3_char_2016_08_01-HR.txt") \
#    + ',' + os.path.join(cal_dir, "PG3_char_2016_11_22-HR-PAC.txt")
MODE = 0664

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]+'/'

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file, CharacterizationRunsFile=char_file,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0004, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

GeneratePythonScript(InputWorkspace="PG3_"+runNumber,
                     Filename=os.path.join(outputDir,"PG3_"+runNumber+'.py'))
ConvertUnits(InputWorkspace='PG3_'+runNumber, OutputWorkspace='PG3_'+runNumber,
    Target='dSpacing',
    EMode='Elastic')

# interactive plots
post_image = True
if post_image:
    div = SavePlot1D(InputWorkspace='PG3_'+runNumber, OutputType='plotly')
    from postprocessing.publish_plot import publish_plot
    request = publish_plot('PG3', runNumber, files={'file':div})
    print "post returned %d" % request.status_code
    print "resulting document:"
    print request.text
else:
    filename = os.path.join(outputDir, 'PG3_%s.html' % runNumber)
    SavePlot1D(InputWorkspace='PG3_'+runNumber, OutputType='plotly-full',
               OutputFilename=filename)
    print 'saved', filename
