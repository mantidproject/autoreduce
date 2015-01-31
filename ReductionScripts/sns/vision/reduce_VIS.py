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
    RunNumber=15225
    NexusFile='/SNS/VIS/'+IPTS+'/nexus/VIS_'+str(RunNumber)+'.nxs.h5'
    FileName='VIS_'+str(RunNumber)+'.nxs.h5'
    SaveDir='/SNS/VIS/shared/VIS_team/YQ/VIS_reduction/epics_tests'

config['defaultsave.directory'] = SaveDir
Root='/SNS/VIS/'+IPTS+'/nexus'  
config.setDataSearchDirs(Root) 

#*********************************************************************
# Save processed nxs file?
# 0: No. 1: Yes
SaveNexusOutput = 1
#*********************************************************************

#*********************************************************************
# At which level the spectrum will be normalized?
# 0: all banks. 1: pixel-by-pixel level
# Note: 0 is faster but 1 is required for Bragg-edge correction
NormLevel = 1
#*********************************************************************

#*********************************************************************
# Where to find monitor data?
# 0: load from current nxs files.  
# 1: open pre-processed/corrected monitor histogram
GetMon = 1
#*********************************************************************
if GetMon == 1:
    # If NormLevel=0, a monitor spectrum in energy transfer is needed
    # If NormLevel=1, a monitor spectrum in wavelength is needed
    #MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorE-corrected-hist.nxs'
    MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorL-corrected-hist.nxs'
    #MonFile = '/SNS/VIS/shared/autoreduce/VIS_5669_ISISMonitorL-corrected-hist.nxs'

#*********************************************************************
# How many monitors in nxs file?
# 1: one-monitor setup. 2: two-monitor secup
# Note: For 2013_2_16B_CAL and run muber after 3009, use 1
MonID = 1
#*********************************************************************

#*********************************************************************
# Is attenuator used for the monitor?
# 0: No. 1: Yes
Attenuator = 0
#*********************************************************************

#*********************************************************************
# Binning parameters
binT='10,1,33333'
binL='0.28,0.001,8.2'
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
PXs=range(2*128+48,2*128+80)+  \
    range(3*128+32,3*128+96)+  \
    range(4*128+32,4*128+96)+  \
    range(5*128+48,5*128+80)
for i in Banks:
    offset=(i-1)*1024
    ListPX=ListPX+[j+offset for j in PXs]
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
# Find monitor spectrum
######################################################################

def FindMonSpec(yvalues):

    mlst = []  
    for i in range(len(yvalues)):
        mlst.append(yvalues[i][0])
    iMax = mlst.index(max(mlst))
    if MonID > 1:
        mlst[iMax] = 0
        iMax=mlst.index(max(mlst))
    return iMax


######################################################################
# Correct monitor spectrum for normalization
######################################################################

def CorrectMonitor(Monitor):

    xvalues = mtd[Monitor].extractX()
    yvalues = mtd[Monitor].extractY()
    evalues = mtd[Monitor].extractE()
    xunit = mtd[Monitor].getAxis(0).getUnit().unitID()
    yunit = mtd[Monitor].YUnit()
    yunitlabel = mtd[Monitor].YUnitLabel()
    for i in range(len(xvalues[0])-1): 
        xm = (xvalues[0][i]+xvalues[0][i+1])/2.0
        if NormLevel == 0:       # Monitor spectrum in deltaE
            xm = xm + 3.5
        elif NormLevel == 1:    # Monitor spectrum in wavelength
            xm = (9.045/xm)**2
        ym = xm**0.5
        if Attenuator==1:
            sigma = 19810.0/xm**0.5051                      # B10 neutron absorption cross-section, in barn
            sigma_vol = sigma*2.7*0.045*0.95/10.013/1.66    # density, weight percent, B10 percent, B10 atomic mass, atomic mass unit
            thickness = 0.08                                # thickness of the absorber/attenuator, in cm
            ym = ym*numpy.exp(sigma_vol*thickness)
        yvalues[0][i]=ym
        evalues[0][i]=0
    __Prefactor=CreateWorkspace(DataX=xvalues,DataY=yvalues,DataE=evalues,NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=Monitor,RHSWorkspace=__Prefactor,OutputWorkspace=Monitor)
    

######################################################################
# Convert an EventWorkspace from distribution to histogram 
######################################################################

def ConvertFromDist(WS):
    xvalues = mtd[WS].extractX()
    yvalues = mtd[WS].extractY()
    evalues = mtd[WS].extractE()
    xunit = mtd[WS].getAxis(0).getUnit().unitID()
    yunit = mtd[WS].YUnit()
    yunitlabel = mtd[WS].YUnitLabel()
    for k in range(len(xvalues[0])-1): 
        yvalues[0][k]=(xvalues[0][k+1]-xvalues[0][k])
        evalues[0][k]=0
    __Prefactor=CreateWorkspace(DataX=xvalues[0],DataY=yvalues[0],DataE=evalues[0],NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=WS,RHSWorkspace=__Prefactor,OutputWorkspace=WS)

######################################################################
# Convert an EventWorkspace from histogram to distribution
######################################################################

def ConvertToDist(WS):
    xvalues = mtd[WS].extractX()
    yvalues = mtd[WS].extractY()
    evalues = mtd[WS].extractE()
    xunit = mtd[WS].getAxis(0).getUnit().unitID()
    yunit = mtd[WS].YUnit()
    yunitlabel = mtd[WS].YUnitLabel()
    for k in range(len(xvalues[0])-1): 
        yvalues[0][k]=1.0/(xvalues[0][k+1]-xvalues[0][k])
        evalues[0][k]=0
    __Prefactor=CreateWorkspace(DataX=xvalues[0],DataY=yvalues[0],DataE=evalues[0],NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=WS,RHSWorkspace=__Prefactor,OutputWorkspace=WS)

######################################################################
# Inelastic data reduction (pixel level, normalization in wavelength)
######################################################################

def ReducePixelsL():

    for i,Pixel in enumerate(ListPX):
        IED_T_Pixel='__T_pixel'
        IED_L_Pixel='__L_pixel'
        IED_E_Pixel='__E_pixel'
        ExtractSingleSpectrum(InputWorkspace='IED_T',OutputWorkspace=IED_T_Pixel,WorkspaceIndex=str(Pixel))
        Ef=CalTab[Pixel][0]
        Df=CalTab[Pixel][1]
        if Ef==0 or Df==0:
            print "Error: Zero Ef or Df, pixel not calibrated"
            sys.exit()
        Efe=(0.7317/Df)**2*Ef
        ConvertUnits(InputWorkspace=IED_T_Pixel,OutputWorkspace=IED_L_Pixel,EMode='Indirect',Target='Wavelength',EFixed=str(Efe))
        RebinToWorkspace(WorkspaceToRebin=IED_L_Pixel,WorkspaceToMatch='DBM_L',OutputWorkspace=IED_L_Pixel,PreserveEvents='1')
        Divide(LHSWorkspace=IED_L_Pixel,RHSWorkspace='DBM_L',OutputWorkspace=IED_L_Pixel)
        ConvertUnits(InputWorkspace=IED_L_Pixel,OutputWorkspace=IED_E_Pixel,EMode='Indirect',Target='DeltaE',EFixed=str(Ef))
        ConvertFromDist(IED_E_Pixel)  
        Rebin(InputWorkspace=IED_E_Pixel,OutputWorkspace=IED_E_Pixel,Params=binE,PreserveEvents='0')
	if i in range(len(BanksForward)*len(PXs)):
            if i==0:
                CloneWorkspace(InputWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Forward')
            else:
                Plus(LHSWorkspace='__IED_E_Forward',RHSWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Forward')
        else:
            if i==len(BanksForward)*len(PXs):
                CloneWorkspace(InputWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Backward')
            else:
                Plus(LHSWorkspace='__IED_E_Backward',RHSWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Backward')

    Plus(LHSWorkspace='__IED_E_Backward',RHSWorkspace='__IED_E_Forward',OutputWorkspace='__IED_E_Average')
    Scale(InputWorkspace='__IED_E_Forward',OutputWorkspace='__IED_E_Forward',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Backward',OutputWorkspace='__IED_E_Backward',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Average',OutputWorkspace='__IED_E_Average',Factor=str(1.0/len(Banks)),Operation='Multiply')
    
    AppendSpectra(InputWorkspace1='__IED_E_Backward',InputWorkspace2='__IED_E_Forward',OutputWorkspace='IED_reduced')
    AppendSpectra(InputWorkspace1='IED_reduced',InputWorkspace2='__IED_E_Average',OutputWorkspace='IED_reduced')
    #ConvertToMatrixWorkspace(InputWorkspace='IED_reduced',OutputWorkspace='IED_reduced')
    ConvertToDistribution('IED_reduced')
    CorrectKiKf(InputWorkspace='IED_reduced',OutputWorkspace='IED_reduced',EMode='Indirect',EFixed='3.5')


######################################################################
# Inelastic data reduction (normalization in deltaE)
######################################################################

def ReduceBanksE():

    for i,Pixel in enumerate(ListPX):
        IED_T_Pixel='__T_pixel'
        IED_E_Pixel='__E_pixel'
        ExtractSingleSpectrum(InputWorkspace='IED_T',OutputWorkspace=IED_T_Pixel,WorkspaceIndex=str(Pixel))
        Ef=CalTab[Pixel][0]
        Df=CalTab[Pixel][1]
        if Ef==0 or Df==0:
            print "Error: Zero Ef or Df, pixel not calibrated"
            sys.exit()
        Efe=(0.7317/Df)**2*Ef
        dE=Efe-Ef
        ConvertUnits(InputWorkspace=IED_T_Pixel,OutputWorkspace=IED_E_Pixel,EMode='Indirect',Target='DeltaE',EFixed=str(Efe))
        ScaleX(InputWorkspace=IED_E_Pixel,OutputWorkspace=IED_E_Pixel,Factor=str(dE),Operation='Add')
        Rebin(InputWorkspace=IED_E_Pixel,OutputWorkspace=IED_E_Pixel,Params=binE,PreserveEvents='1')
	if i in range(len(BanksForward)*len(PXs)):
            if i==0:
                CloneWorkspace(InputWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Forward')
            else:
                Plus(LHSWorkspace='__IED_E_Forward',RHSWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Forward')
        else:
            if i==len(BanksForward)*len(PXs):
                CloneWorkspace(InputWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Backward')
            else:
                Plus(LHSWorkspace='__IED_E_Backward',RHSWorkspace=IED_E_Pixel,OutputWorkspace='__IED_E_Backward')
		
    Plus(LHSWorkspace='__IED_E_Backward',RHSWorkspace='__IED_E_Forward',OutputWorkspace='__IED_E_Average')
    Scale(InputWorkspace='__IED_E_Forward',OutputWorkspace='__IED_E_Forward',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Backward',OutputWorkspace='__IED_E_Backward',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')
    Scale(InputWorkspace='__IED_E_Average',OutputWorkspace='__IED_E_Average',Factor=str(1.0/len(Banks)),Operation='Multiply')
    
    AppendSpectra(InputWorkspace1='__IED_E_Backward',InputWorkspace2='__IED_E_Forward',OutputWorkspace='IED_reduced')
    AppendSpectra(InputWorkspace1='IED_reduced',InputWorkspace2='__IED_E_Average',OutputWorkspace='IED_reduced')
    RebinToWorkspace(WorkspaceToRebin='IED_reduced',WorkspaceToMatch='DBM_E',OutputWorkspace='IED_reduced',PreserveEvents='0')
    Divide(LHSWorkspace='IED_reduced',RHSWorkspace='DBM_E',OutputWorkspace='IED_reduced')
    CorrectKiKf(InputWorkspace='IED_reduced',OutputWorkspace='IED_reduced',EMode='Indirect',EFixed='3.5')


######################################################################
# Main program
######################################################################

#subprocess.call(["/SNS/VIS/shared/autoreduce/update_VIS.sh", IPTS])
#subprocess.call(["/SNS/VIS/shared/autoreduce/update_VIS.sh"])

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

if GetMon==0:
    print 'Loading monitor data from', NexusFile
    LoadNexusMonitors(Filename=NexusFile,OutputWorkspace='__monitor')
    yvalues = mtd['__monitor'].extractY()
    iSpec = FindMonSpec(yvalues)
    ExtractSingleSpectrum(InputWorkspace='__monitor',OutputWorkspace='DBM_T',WorkspaceIndex=str(iSpec))
    if mtd['DBM_T'].getRun().getProtonCharge() < 5.0:
        print "Error: Proton charge is too low"
        sys.exit()
    print 'Processing monitor data'
    NormaliseByCurrent(InputWorkspace='DBM_T',OutputWorkspace='DBM_T')
    RemoveArtifact('DBM_T',10,33333,16660,12)

print 'Loading inelastic banks from', NexusFile
bank_list = ["bank%d" % i for i in range(1, 15)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, OutputWorkspace='IED_T', LoadMonitors='0')
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

if NormLevel == 0:
    if GetMon == 0:
        ConvertUnits(InputWorkspace='DBM_T',OutputWorkspace='DBM_E',Target='Energy')
        ConvertUnits(InputWorkspace='DBM_E',OutputWorkspace='DBM_E',Target='DeltaE',EMode='Indirect',EFixed='3.5')
        ScaleX(InputWorkspace='DBM_E',OutputWorkspace='DBM_E',Factor='-3.5',Operation='Add')
        Rebin(InputWorkspace='DBM_E',OutputWorkspace='DBM_E',Params=binE,PreserveEvents='0')
        CorrectMonitor('DBM_E')
        SmoothData(InputWorkspace='DBM_E',OutputWorkspace='DBM_E',NPoints='201')
    elif GetMon == 1:
        LoadNexusProcessed(Filename=MonFile,OutputWorkspace='DBM_E',LoadHistory=False)
    ReduceBanksE()

elif NormLevel == 1:
    if GetMon == 0:
        ConvertUnits(InputWorkspace='DBM_T',OutputWorkspace='DBM_L',Target='Wavelength')
        Rebin(InputWorkspace='DBM_L',OutputWorkspace='DBM_L',Params=binL,PreserveEvents='0')
        CorrectMonitor('DBM_L')
        FFTSmooth(InputWorkspace='DBM_L',OutputWorkspace='DBM_L',Filter='Zeroing',Params='20')
    elif GetMon == 1:
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

'''
asciidir=os.path.join(SaveDir,"ascii")
if not os.path.exists(asciidir):
    os.makedirs(asciidir)
    print "Info: "+asciidir+" does not exist and will be created."
OutFile=os.path.join(asciidir,'VIS_'+INS+'.dat')
SaveAscii(InputWorkspace=INS,Filename=OutFile,Separator='Space')

######################################################################
# Save Inelastic banks in a separate file
######################################################################
sliced_dir = os.path.join(SaveDir, "sliced_data")
if not os.path.exists(sliced_dir):
    os.makedirs(sliced_dir)

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
