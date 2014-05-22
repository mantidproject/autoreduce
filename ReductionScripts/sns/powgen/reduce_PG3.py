import os
import sys
import shutil 
#sys.path.append("/opt/Mantid/bin")
sys.path.append("/opt/mantidnightly/bin")
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from mantid.simpleapi import *
import mantid
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
cal_dir = "/SNS/PG3/2014_1_11A_CAL/"
cal_file  = os.path.join(cal_dir, "PG3_PAC_d17532_2014_02_14.cal")
char_file = os.path.join(cal_dir, "PG3_characterization_2014_02_11-HR-PAC-BGsub.txt")
#MODE = 0664

#from mantidsimple import *

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]

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
                   Binning=-0.0008, BinInDspace=True, FilterBadPulses=True,
                   ScaleData =100,
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

s=mtd["PG3_"+runNumber]
x=s.readX(0)
y=s.readY(0)
plot(x[1:],y)
xlabel('d($\AA$)')
ylabel('Intensity')
#yscale('log')
show()
savefig(outputDir+"PG3_"+runNumber+'.png',bbox_inches='tight')

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
