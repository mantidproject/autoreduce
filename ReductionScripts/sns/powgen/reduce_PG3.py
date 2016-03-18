import os
import sys
import shutil 
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
import mantid
from matplotlib import *
cal_dir = "/SNS/PG3/shared/CALIBRATION/2016_1_11A_CAL/"
cal_file  = os.path.join(cal_dir, "PG3_PAC_d27021_2016_02_12.h5")
char_file = os.path.join(cal_dir, "PG3_char_2016_03_10-HR-MICAS-8mm-AL.txt")
#MODE = 0664

#from mantidsimple import *

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]+'/'

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

SNSPowderReduction(Instrument="PG3", RunNumber=runNumber, Extension="_event.nxs",
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file, CharacterizationRunsFile=char_file,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0008, BinInDspace=True, 
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

SavePlot1D(InputWorkspace="PG3_"+runNumber, OutputFilename=outputDir+"PG3_"+runNumber+'.png',  YLabel='Intensity')

#dirList=os.listdir(outputDir)
#for fname in dirList:
#  os.chmod(os.path.join(outputdir, fname), MODE)

#fileName= "PG3_" + runNumber + "_REDUCED.gsa"
#outputFile=outputDir+"/"+fileName
#f=open(outputFile, 'w')
#f.write('POWGEN auto data reduction results')
#
#fileName2= "PG3_" + runNumber + "_REDUCED2.gsa"
#outputFile2=outputDir+"/"+fileName2
#f2=open(outputFile2, 'w')
#f2.write('More POWGEN auto data reduction results')
#
#print outputFile + " is created"
#print outputFile2 + " is created"
