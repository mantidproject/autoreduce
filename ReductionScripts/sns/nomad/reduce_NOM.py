import os
import sys
import shutil 
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid

cal_dir = "/SNS/NOM/IPTS-14341/shared"
NOM_calibrate_d49573_2015_09_02.calcNOM_calibrate_d49573_2015_09_02.calaNOM_calibrate_d49573_2015_09_02.callNOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.calfNOM_calibrate_d49573_2015_09_02.caliNOM_calibrate_d49573_2015_09_02.callNOM_calibrate_d49573_2015_09_02.caleNOM_calibrate_d49573_2015_09_02.cal NOM_calibrate_d49573_2015_09_02.cal NOM_calibrate_d49573_2015_09_02.cal=NOM_calibrate_d49573_2015_09_02.cal NOM_calibrate_d49573_2015_09_02.caloNOM_calibrate_d49573_2015_09_02.calsNOM_calibrate_d49573_2015_09_02.cal.NOM_calibrate_d49573_2015_09_02.calpNOM_calibrate_d49573_2015_09_02.calaNOM_calibrate_d49573_2015_09_02.caltNOM_calibrate_d49573_2015_09_02.calhNOM_calibrate_d49573_2015_09_02.cal.NOM_calibrate_d49573_2015_09_02.caljNOM_calibrate_d49573_2015_09_02.caloNOM_calibrate_d49573_2015_09_02.caliNOM_calibrate_d49573_2015_09_02.calnNOM_calibrate_d49573_2015_09_02.cal(NOM_calibrate_d49573_2015_09_02.calcNOM_calibrate_d49573_2015_09_02.calaNOM_calibrate_d49573_2015_09_02.callNOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.caldNOM_calibrate_d49573_2015_09_02.caliNOM_calibrate_d49573_2015_09_02.calrNOM_calibrate_d49573_2015_09_02.cal,NOM_calibrate_d49573_2015_09_02.cal NOM_calibrate_d49573_2015_09_02.cal"NOM_calibrate_d49573_2015_09_02.calNNOM_calibrate_d49573_2015_09_02.calONOM_calibrate_d49573_2015_09_02.calMNOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.calcNOM_calibrate_d49573_2015_09_02.calaNOM_calibrate_d49573_2015_09_02.callNOM_calibrate_d49573_2015_09_02.caliNOM_calibrate_d49573_2015_09_02.calbNOM_calibrate_d49573_2015_09_02.calrNOM_calibrate_d49573_2015_09_02.calaNOM_calibrate_d49573_2015_09_02.caltNOM_calibrate_d49573_2015_09_02.caleNOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.caldNOM_calibrate_d49573_2015_09_02.cal4NOM_calibrate_d49573_2015_09_02.cal9NOM_calibrate_d49573_2015_09_02.cal5NOM_calibrate_d49573_2015_09_02.cal7NOM_calibrate_d49573_2015_09_02.cal3NOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.cal2NOM_calibrate_d49573_2015_09_02.cal0NOM_calibrate_d49573_2015_09_02.cal1NOM_calibrate_d49573_2015_09_02.cal5NOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.cal0NOM_calibrate_d49573_2015_09_02.cal9NOM_calibrate_d49573_2015_09_02.cal_NOM_calibrate_d49573_2015_09_02.cal0NOM_calibrate_d49573_2015_09_02.cal2NOM_calibrate_d49573_2015_09_02.cal.NOM_calibrate_d49573_2015_09_02.calhNOM_calibrate_d49573_2015_09_02.cal5NOM_calibrate_d49573_2015_09_02.cal"NOM_calibrate_d49573_2015_09_02.cal)NOM_calibrate_d49573_2015_09_02.cal
NOM_calibrate_d49573_2015_09_02.cal
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
