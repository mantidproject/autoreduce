import os
import sys
import shutil 
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid

cal_dir = "/SNS/NOM/IPTS-14341/shared"
NOM_calibrate_d_495732015_09_02.h5cNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5lNOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h5fNOM_calibrate_d_495732015_09_02.h5iNOM_calibrate_d_495732015_09_02.h5lNOM_calibrate_d_495732015_09_02.h5eNOM_calibrate_d_495732015_09_02.h5 NOM_calibrate_d_495732015_09_02.h5 NOM_calibrate_d_495732015_09_02.h5=NOM_calibrate_d_495732015_09_02.h5 NOM_calibrate_d_495732015_09_02.h5oNOM_calibrate_d_495732015_09_02.h5sNOM_calibrate_d_495732015_09_02.h5.NOM_calibrate_d_495732015_09_02.h5pNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5tNOM_calibrate_d_495732015_09_02.h5hNOM_calibrate_d_495732015_09_02.h5.NOM_calibrate_d_495732015_09_02.h5jNOM_calibrate_d_495732015_09_02.h5oNOM_calibrate_d_495732015_09_02.h5iNOM_calibrate_d_495732015_09_02.h5nNOM_calibrate_d_495732015_09_02.h5(NOM_calibrate_d_495732015_09_02.h5cNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5lNOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h5dNOM_calibrate_d_495732015_09_02.h5iNOM_calibrate_d_495732015_09_02.h5rNOM_calibrate_d_495732015_09_02.h5,NOM_calibrate_d_495732015_09_02.h5 NOM_calibrate_d_495732015_09_02.h5"NOM_calibrate_d_495732015_09_02.h5NNOM_calibrate_d_495732015_09_02.h5ONOM_calibrate_d_495732015_09_02.h5MNOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h5cNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5lNOM_calibrate_d_495732015_09_02.h5iNOM_calibrate_d_495732015_09_02.h5bNOM_calibrate_d_495732015_09_02.h5rNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5tNOM_calibrate_d_495732015_09_02.h5eNOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h5dNOM_calibrate_d_495732015_09_02.h54NOM_calibrate_d_495732015_09_02.h59NOM_calibrate_d_495732015_09_02.h55NOM_calibrate_d_495732015_09_02.h57NOM_calibrate_d_495732015_09_02.h53NOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h52NOM_calibrate_d_495732015_09_02.h50NOM_calibrate_d_495732015_09_02.h51NOM_calibrate_d_495732015_09_02.h55NOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h50NOM_calibrate_d_495732015_09_02.h58NOM_calibrate_d_495732015_09_02.h5_NOM_calibrate_d_495732015_09_02.h53NOM_calibrate_d_495732015_09_02.h51NOM_calibrate_d_495732015_09_02.h5.NOM_calibrate_d_495732015_09_02.h5cNOM_calibrate_d_495732015_09_02.h5aNOM_calibrate_d_495732015_09_02.h5lNOM_calibrate_d_495732015_09_02.h5"NOM_calibrate_d_495732015_09_02.h5)NOM_calibrate_d_495732015_09_02.h5
NOM_calibrate_d_495732015_09_02.h5
char_file = "/SNS/NOM/shared/NOM_characterizations.txt" #os.path.join(cal_dir, "NOM_characterizations.txt")
sam_back =     49577
van      =     49575
van_back =     49576

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
                   ResampleX=-3000, BinInDspace=True, FilterBadPulses=25.,
                   SaveAs="gsas and fullprof and pdfgetn", OutputDirectory=outputDir,
                   StripVanadiumPeaks=True,
                   NormalizeByCurrent=True, FinalDataUnits="MomentumTransfer")
