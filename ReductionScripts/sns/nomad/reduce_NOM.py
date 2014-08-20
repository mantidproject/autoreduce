import os
import sys
import shutil 
import shlex
from os import listdir
from time import sleep
from subprocess import Popen
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid


cal_dir = "/SNS/NOM/IPTS-12255/shared"

cal_file  = os.path.join(cal_dir, "NOM_calibrate_d32221_2014_08_20.cal")
char_file = "/SNS/NOM/shared/NOM_characterizations.txt" #os.path.join(cal_dir, "NOM_characterizations.txt")
sam_back =     32222
van      =     32223
van_back =     32224
ipts     =    '10957'

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

tempplotdir='/SNS/NOM/IPTS-'+ipts+'/shared/autoNOM/figs/'
tempplotfile='NOM_'+runNumber+'_autoreduced_temp.png'
plotdir='/SNS/NOM/IPTS-'+ipts+'/shared/autoreduce/'
plotfile='NOM_'+runNumber+'_autoreduced.png'

plotexist= (tempplotfile in a)

if plotexist:
    lline='cp '+ tempplotdir + tempplotfile +' '+ plotdir + plotfile
    Popen(shlex.split(lline))
