######################################################################
# Python script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv
import string
import subprocess

# Please check/change the following parameters
#=====================================================================
#=====================================================================

#*********************************************************************
# How would you like to run the script?
# 0: command-line mode. 1: GUI-mode
Interface = 0
#*********************************************************************
if Interface == 0:
    sys.path.append("/opt/Mantid/bin")
    from mantid.simpleapi import *
    NexusFile = os.path.abspath(sys.argv[1])
    FileName = NexusFile.split(os.sep)[-1]
    IPTS = NexusFile.split(os.sep)[-3]
    RunNumber = int(FileName.strip('VIS_').replace('.nxs.h5',''))
    SaveDir = sys.argv[2]
elif Interface == 1:
    IPTS='IPTS-6966'
    RunNumber=16933
    NexusFile='/SNS/VIS/'+IPTS+'/nexus/VIS_'+str(RunNumber)+'.nxs.h5'
    FileName='VIS_'+str(RunNumber)+'.nxs.h5'
    SaveDir='/SNS/VIS/shared/VIS_team/YQ'

config['defaultsave.directory'] = SaveDir
Root='/SNS/VIS/'+IPTS+'/nexus'  
config.setDataSearchDirs(Root) 
MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorL-corrected-hist.nxs'
#MonFile = '/SNS/VIS/shared/autoreduce/VIS_5669_ISISMonitorL-corrected-hist.nxs'

#*********************************************************************
# Save processed nxs file?
# 0: No. 1: Yes
SaveNexusOutput = 1
#*********************************************************************


#*********************************************************************
# Binning parameters
binT='10,1,33333'
binL='0.281,0.0002,8.199'
binE='-2,0.005,5,-0.001,1000'
#*********************************************************************

#*********************************************************************
# Banks to be reduced
BanksForward=[2,3,4,5,6]
BanksBackward=[8,9,10,11,12,13,14]
Banks=BanksForward+BanksBackward
#*********************************************************************

#*********************************************************************
# Pixels to be reduced
ListPX = []
ListPXF = []
ListPXB = []
PXs=range(2*128+48,2*128+80)+  \
    range(3*128+32,3*128+96)+  \
    range(4*128+32,4*128+96)+  \
    range(5*128+48,5*128+80)
for i in BanksForward:
    offset=(i-1)*1024
    ListPX=ListPX+[j+offset for j in PXs]
    ListPXF=ListPXF+[j+offset for j in PXs]
for i in BanksBackward:
    offset=(i-1)*1024
    ListPX=ListPX+[j+offset for j in PXs]
    ListPXB=ListPXB+[j+offset for j in PXs]

# Create a list of pixels to mask
# Inelastic Pixels = 0-14335
allPixels = set(range(14336))
toKeep = set(ListPX)
mask = allPixels.difference(toKeep)
MaskPX = list(mask)

#*********************************************************************

#*********************************************************************
# Calibration table
CalFile='/SNS/VIS/shared/autoreduce/VIS_CalTab-03-03-2014.csv'
#*********************************************************************

#=====================================================================
#=====================================================================









######################################################################
# Make a valid file name from a string
######################################################################

def FormatFilename(s):
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    outfilename = ''.join(c for c in s if c in valid_chars)
    outfilename = outfilename.replace(' ','_')
    return outfilename


######################################################################
# Remove artifacts such as prompt pulse
######################################################################

def RemoveArtifact(WS,Xmin,Xmax,Xa,Delta):

    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux0',XMin=str(Xmin),XMax=str(Xa))
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux3',XMin=str(Xa+Delta),XMax=str(Xmax))
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux1',XMin=str(Xa-Delta),XMax=str(Xa))
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux2',XMin=str(Xa+Delta),XMax=str(Xa+2*Delta ) )
    
    ScaleX(InputWorkspace='__aux1',OutputWorkspace='__aux1',Factor=str(Delta),Operation='Add')
    ScaleX(InputWorkspace='__aux2',OutputWorkspace='__aux2',Factor=str(-Delta),Operation='Add')
    Scale(InputWorkspace='__aux1',OutputWorkspace='__aux1',Factor='0.5',Operation='Multiply')
    Scale(InputWorkspace='__aux2',OutputWorkspace='__aux2',Factor='0.5',Operation='Multiply')

    Plus(LHSWorkspace='__aux0',RHSWorkspace='__aux1',OutputWorkspace=WS)
    Plus(LHSWorkspace=WS,RHSWorkspace='__aux2',OutputWorkspace=WS)
    Plus(LHSWorkspace=WS,RHSWorkspace='__aux3',OutputWorkspace=WS)

    
######################################################################
# Inelastic data reduction (pixel level, normalization in wavelength)
######################################################################

def ReducePixelsL():

    for i,Pixel in enumerate(ListPX):
        Ef=CalTab[Pixel][0]
        Df=CalTab[Pixel][1]
        Efe=(0.7317/Df)**2*Ef
        mtd['IED_T'].setEFixed(Pixel, Efe)
    ConvertUnits(InputWorkspace='IED_T',OutputWorkspace='IED_L',EMode='Indirect',Target='Wavelength')
    Rebin(InputWorkspace='IED_L',OutputWorkspace='IED_L',Params=binL,PreserveEvents='0')
    InterpolatingRebin(InputWorkspace='DBM_L',OutputWorkspace='DBM_L',Params=binL)
    #RebinToWorkspace(WorkspaceToRebin='DBM_L',WorkspaceToMatch='IED_L',OutputWorkspace='DBM_L')
    Divide(LHSWorkspace='IED_L',RHSWorkspace='DBM_L',OutputWorkspace='IED_L')
    for i,Pixel in enumerate(ListPX):
        Ef=CalTab[Pixel][0]
        mtd['IED_L'].setEFixed(Pixel, Ef)
    ConvertUnits(InputWorkspace='IED_L',OutputWorkspace='IED_E',EMode='Indirect',Target='DeltaE')
    Rebin(InputWorkspace='IED_E',OutputWorkspace='IED_E',Params=binE,PreserveEvents='0')
    CorrectKiKf(InputWorkspace='IED_E',OutputWorkspace='IED_E',EMode='Indirect')

    GroupDetectors(InputWorkspace='IED_E',OutputWorkspace='__IED_E_Forward',DetectorList=ListPXF)
    GroupDetectors(InputWorkspace='IED_E',OutputWorkspace='__IED_E_Backward',DetectorList=ListPXB)
    GroupDetectors(InputWorkspace='IED_E',OutputWorkspace='__IED_E_Average',DetectorList=ListPX)

    Scale(InputWorkspace='__IED_E_Forward',OutputWorkspace='__IED_E_Forward',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Backward',OutputWorkspace='__IED_E_Backward',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Average',OutputWorkspace='__IED_E_Average',Factor=str(1.0/len(Banks)),Operation='Multiply')
    
    AppendSpectra(InputWorkspace1='__IED_E_Backward',InputWorkspace2='__IED_E_Forward',OutputWorkspace='IED_reduced')
    AppendSpectra(InputWorkspace1='IED_reduced',InputWorkspace2='__IED_E_Average',OutputWorkspace='IED_reduced')


######################################################################
# Main program
######################################################################

# Read calibration table
CalTab = [[0 for _ in range(2)] for _ in range(1024*14)]
tab = list(csv.reader(open(CalFile,'r')))
for i in range(0,len(tab)):
    for j in [0,1]:
        tab[i][j]=int(tab[i][j])
    for j in [2,3]:
        tab[i][j]=float(tab[i][j])
    j=(tab[i][0]-1)*1024+tab[i][1]
    CalTab[j][0]=tab[i][2]
    CalTab[j][1]=tab[i][3]

print 'Loading inelastic banks from', NexusFile
bank_list = ["bank%d" % i for i in range(1, 15)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, OutputWorkspace='IED_T', LoadMonitors='0')
LoadInstrument(Workspace='IED_T',Filename='/SNS/VIS/shared/autoreduce/VISION_Definition_no_efixed.xml')
MaskDetectors(Workspace='IED_T', DetectorList=MaskPX)

print "Title:", mtd['IED_T'].getTitle()
print "Proton charge:", mtd['IED_T'].getRun().getProtonCharge()
if "Temperature" in mtd['IED_T'].getTitle():
    print "Error: Non-equilibrium runs will not be reduced"
    sys.exit()
if mtd['IED_T'].getRun().getProtonCharge() < 5.0:
    print "Error: Proton charge is too low"
    sys.exit()

NormaliseByCurrent(InputWorkspace='IED_T',OutputWorkspace='IED_T')
RemoveArtifact('IED_T',10,33333,16660,240)


LoadNexusProcessed(Filename=MonFile,OutputWorkspace='DBM_L',LoadHistory=False)

ReducePixelsL()

Title = mtd['IED_reduced'].getTitle()
Note = Title.split('>')[0]
Note = FormatFilename(Note)
INS = str(RunNumber)+'_'+Note

Scale(InputWorkspace='IED_reduced',OutputWorkspace=INS,Factor='500',Operation='Multiply')
mtd[INS].setYUnitLabel('Normalized intensity')

if SaveNexusOutput==0:
    print "Warning: Reduced data NOT saved."
    sys.exit()

RemoveLogs(INS)
RemoveWorkspaceHistory(INS)
SaveNexusProcessed(InputWorkspace=INS,Filename='VIS_'+INS+'.nxs')

asciidir=os.path.join(SaveDir,"ascii")
if not os.path.exists(asciidir):
    os.umask(0002)
    os.makedirs(asciidir,0775)
    print "Info: "+asciidir+" does not exist and will be created."
OutFile=os.path.join(asciidir,'VIS_'+INS+'.dat')
SaveAscii(InputWorkspace=INS,Filename=OutFile,Separator='Space')

'''
subprocess.call(["/SNS/VIS/shared/autoreduce/update_VIS.sh", IPTS])
#subprocess.call(["/SNS/VIS/shared/autoreduce/update_VIS.sh"])

######################################################################
# Save Inelastic banks in a separate file
######################################################################
sliced_dir = os.path.join(SaveDir, "sliced_data")
if not os.path.exists(sliced_dir):
    os.umask(0002)
    os.makedirs(sliced_dir,0775)

from mantid.api import AnalysisDataService
for item in AnalysisDataService.getObjectNames():
    AnalysisDataService.remove(item)

bank_list = ["bank%d" % i for i in range(1, 15)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, OutputWorkspace="__inelastic_data", LoadMonitors=True)
inelastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_inelastic.nxs.h5'))
SaveNexus(InputWorkspace="__inelastic_data", Filename=inelastic_file)
Rebin(InputWorkspace='__inelastic_data_monitors',OutputWorkspace='__inelastic_data_monitors',Params="1,1,35000",PreserveEvents='0')
monitor_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_monitors.nxs.h5'))
SaveNexus(InputWorkspace="__inelastic_data_monitors", Filename=monitor_file)
AnalysisDataService.remove("__inelastic_data")
AnalysisDataService.remove("__inelastic_data_monitors")

bank_list = ["bank%d" % i for i in range(15, 25)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace="__elastic_back_data")
Rebin(InputWorkspace='__elastic_back_data',OutputWorkspace='__elastic_back_data',Params="10,1,2000,-0.0005,35000",PreserveEvents='0')
CropWorkspace(InputWorkspace='__elastic_back_data', OutputWorkspace='__elastic_back_data', StartWorkspaceIndex=14336, EndWorkspaceIndex=34815)
elastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_elastic_backscattering.nxs.h5'))
SaveNexus(InputWorkspace="__elastic_back_data", Filename=elastic_file)
AnalysisDataService.remove("__elastic_back_data")

bank_list = ["bank%d" % i for i in range(25, 31)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace="__elastic_data")
Rebin(InputWorkspace='__elastic_data',OutputWorkspace='__elastic_data',Params="10,1,2000,-0.0005,35000",PreserveEvents='0')
elastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_elastic.nxs.h5'))
SaveNexus(InputWorkspace="__elastic_data", Filename=elastic_file)
AnalysisDataService.remove("__elastic_data")
'''
