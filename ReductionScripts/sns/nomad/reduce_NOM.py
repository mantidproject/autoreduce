import os
import sys
import shutil
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid

cal_dir = "/SNS/NOM/IPTS-9577/shared"
cal_file  = os.path.join(cal_dir, "autoreduce", "NOM_calibrate_d22265_2013_11_27.cal")
char_file = "/SNS/NOM/shared/NOM_characterizations.txt" #os.path.join(cal_dir, "NOM_characterizations.txt")
sam_back =     22269
van      =     22215
van_back =     22268

#from mantidsimple import *

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]
maxChunkSize=0.
if len(sys.argv)>3:
maxChunkSize=float(sys.argv[3])

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

SNSPowderReduction(Instrument="NOM", RunNumber=runNumber, Extension="_event.nxs",
MaxChunkSize=maxChunkSize, PreserveEvents=True,PushDataPositive='AddMinimum',
CalibrationFile=cal_file, CharacterizationRunsFile=char_file,
BackgroundNumber=sam_back, VanadiumNumber=van,
VanadiumBackgroundNumber=van_back, RemovePromptPulseWidth=50,
ResampleX=-3000, BinInDspace=True, FilterBadPulses=True,
SaveAs="gsas and fullprof and pdfgetn", OutputDirectory=outputDir,
StripVanadiumPeaks=True,
NormalizeByCurrent=True, FinalDataUnits="MomentumTransfer")
