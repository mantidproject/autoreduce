######################################################################
# Python Script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv

sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *

nexus_file=sys.argv[1]
output_directory=sys.argv[2]

global filename
global run_number
filename = os.path.split(nexus_file)[-1]
run_number = filename.strip('VIS_').replace('.nxs.h5','')

# Please check and change the following parameters
#=====================================================================

# Output files to be saved in
SaveDirectory=output_directory

# 1 for 7-bank setup (2013-2 and before), 2 for 12-bank setup (since 2014-1 cycle)
BankVersion=2

global MonitorID
# Which monitor to use (1 for 1-monitor setup, 2 for 2-monitor setup)
# For 2013_2_16B_CAL and run muber after 3009 in 2014-1, use 1
MonitorID=1

# Align elastic lines
global ShiftTag
ShiftTag=0

global ScaleTag
ScaleTag=0
global ScaleXMin
ScaleXMin=50
global ScaleXMax
ScaleXMax=500

# Binning parameter
binE=0.001

#=====================================================================


global BanksForward 
global BanksBackward 
if BankVersion==1:
    BanksForward=[2]
    BanksBackward=[9,10,11,12,13,14]
elif BankVersion==2:
    BanksForward=[2,3,4,5,6]
    BanksBackward=[8,9,10,11,12,13,14]
else:
    print "Error: BankVersion should be 1 or 2"
    sys.exit()
global Banks 
Banks=BanksForward+BanksBackward

config['defaultsave.directory'] = SaveDirectory
CalFile='/SNS/VIS/shared/VIS_Reduction/VIS_CalTab-03-03-2014.csv'

# Pixels to be included
ListPX=range(2*128+48,2*128+80)+  \
       range(3*128+32,3*128+96)+  \
       range(4*128+32,4*128+96)+  \
       range(5*128+48,5*128+80)

# Read calibration table
CalTab = [[[0 for _ in range(2)] for _ in range(1024)] for _ in range(14)]
tab = list(csv.reader(open(CalFile,'r')))
for i in range(0,len(tab)):
    for j in [0,1]:
        tab[i][j]=int(tab[i][j])
    for j in [2,3]:
        tab[i][j]=float(tab[i][j])
    CalTab[tab[i][0]-1][tab[i][1]][0]=tab[i][2]
    CalTab[tab[i][0]-1][tab[i][1]][1]=tab[i][3]


######################################################################
# Rebinning Intervals
######################################################################

def IntervalsRebinning(deltaE):
    return '-2,'+str(deltaE*5)+',5,'+str(-deltaE)+',1000'


######################################################################
# Calculate Pearson correlation coefficients
######################################################################

def pearson(x,y):
    scorex = []
    scorey = []
    xmean=numpy.mean(x)
    ymean=numpy.mean(y)
    xstd=numpy.std(x)
    ystd=numpy.std(y)
    for i in x:
        scorex.append((i - xmean)/xstd)
    for j in y:
        scorey.append((j - ymean)/ystd)
    return (sum([i*j for i,j in zip(scorex,scorey)]))/(len(x))


######################################################################
# Remove Prompt Pulse or other artifacts
######################################################################

def RemovePromptToF(WS,TPrompt,Delta):

    NDeltas=1

    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux0',XMin='100',XMax=str(TPrompt))
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux3',XMin=str(TPrompt+Delta),XMax='33333')
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux1',XMin=str(TPrompt-Delta),XMax=str(TPrompt))
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__aux2',XMin=str(TPrompt+NDeltas*Delta),XMax=str(TPrompt+NDeltas*Delta+Delta ) )
    
    ScaleX(InputWorkspace='__aux1',OutputWorkspace='__aux1',Factor=str(Delta),Operation='Add')
    ScaleX(InputWorkspace='__aux2',OutputWorkspace='__aux2',Factor=str(-NDeltas*Delta),Operation='Add')
    Scale(InputWorkspace='__aux1',OutputWorkspace='__aux1',Factor='0.5',Operation='Multiply')
    Scale(InputWorkspace='__aux2',OutputWorkspace='__aux2',Factor='0.5',Operation='Multiply')

    Plus(LHSWorkspace='__aux0',RHSWorkspace='__aux1',OutputWorkspace=WS)
    Plus(LHSWorkspace=WS,RHSWorkspace='__aux2',OutputWorkspace=WS)
    Plus(LHSWorkspace=WS,RHSWorkspace='__aux3',OutputWorkspace=WS)
    

######################################################################
# Find Monitor Spectrum
######################################################################

def FindMonSpec(yvalues):

    mlst = []  
    for i in range(len(yvalues)):
        mlst.append(yvalues[i][0])
    iMax=mlst.index(max(mlst))
    if MonitorID>1:
        mlst[iMax]=0
        iMax=mlst.index(max(mlst))
    return iMax


######################################################################
# Load Monitors 
######################################################################

def LoadMonitor(binE):
    
    LoadNexusMonitors(Filename=filename,OutputWorkspace='__monitor')
    yvalues = mtd['__monitor'].extractY()
    iSpec = FindMonSpec(yvalues)
    ExtractSingleSpectrum(InputWorkspace='__monitor',OutputWorkspace='MonitorT',WorkspaceIndex=str(iSpec))
    RemovePromptToF('MonitorT',16600,1400)        
    NormaliseByCurrent(InputWorkspace='MonitorT',OutputWorkspace='MonitorT')
    ConvertUnits(InputWorkspace='MonitorT',OutputWorkspace='MonitorE',Target='Energy')
    ConvertUnits(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Target='DeltaE',EMode='Indirect',EFixed='3.5')
    ScaleX(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Factor='-3.5',Operation='Add')
    Rebin(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Params= IntervalsRebinning(binE),PreserveEvents='0')
    
    xvalues = mtd['MonitorE'].extractX()
    yvalues = mtd['MonitorE'].extractY()
    evalues = mtd['MonitorE'].extractE()
    xunit = mtd['MonitorE'].getAxis(0).getUnit().unitID()
    yunit = mtd['MonitorE'].YUnit()
    yunitlabel = mtd['MonitorE'].YUnitLabel()
    for i in range(len(xvalues[0])-1):
        xm = (xvalues[0][i]+xvalues[0][i+1])/2.0
        sigma = 19810.0/(xm+3.5)**0.5051                # B10 neutron absorption cross-section, in barn
        sigma_vol = sigma*2.7*0.045*0.95/10.013/1.66    # density, weight percent, B10 percent, B10 atomic mass, atomic mass unit
        thickness = 0.08                                # thickness of the absorber/attenuator, in cm
        ym = (xm+3.5)**0.5*numpy.exp(sigma_vol*thickness)
        yvalues[0][i]=ym
        evalues[0][i]=0
    Prefactor=CreateWorkspace(DataX=xvalues,DataY=yvalues,DataE=evalues,NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace='MonitorE',RHSWorkspace=Prefactor,OutputWorkspace='SampleE')

    ConvertToDistribution(Workspace='SampleE')
    SmoothData(InputWorkspace='SampleE',OutputWorkspace='SampleE',NPoints='201')
    ConvertToDistribution(Workspace='MonitorE')
    SmoothData(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',NPoints='201')

    return 'MonitorT','MonitorE',Prefactor,'SampleE'


######################################################################
# Load Inelastic Banks
######################################################################

def LoadInelasticBanks():
    
    BanksT = []
    BanksTsum = []
    for i,BankNum in enumerate(Banks):
        BanksT.append('BankT_'+str(BankNum))
        BankLoad='bank'+str(BankNum)
        LoadEventNexus(Filename=filename,OutputWorkspace=BanksT[i],SingleBankPixelsOnly=True,BankName=BankLoad,CompressTolerance='-1',FilterByTofMin=100,FilterByTofMax=33333,LoadLogs='1')
        RemovePromptToF(BanksT[i],16605,320)
        NormaliseByCurrent(InputWorkspace=BanksT[i],OutputWorkspace=BanksT[i])
        #Rebin(InputWorkspace=BanksT[i],OutputWorkspace='__extra',Params='5000,1,23000',PreserveEvents='0')
        #BanksTsum.append('BankTsum_'+str(BankNum))
        #SumSpectra(InputWorkspace='__extra',OutputWorkspace=BanksTsum[i])

    return BanksT



######################################################################
# Inelastic Data Reduction
######################################################################

def ReduceINS(BanksT,ListPX,CalTab,binE):
    BanksE=[]
    BanksEsum=[]
    for i, Bank in enumerate(BanksT):    
        print 'Reducing data in Bank #', Banks[i]
        BanksE.append('__BankE_'+str(Banks[i]))
        BanksEsum.append('__BankEsum_'+str(Banks[i]))
        for j,Pixel in enumerate(ListPX):
            BankTPixel='__bankT_pixel'
            BankEPixel='__bankE_pixel'
            ExtractSingleSpectrum(InputWorkspace=Bank,OutputWorkspace=BankTPixel,WorkspaceIndex=str(Pixel))
            Ef=CalTab[Banks[i]-1][Pixel][0]
            Df=CalTab[Banks[i]-1][Pixel][1]
            if Ef==0 or Df==0:
                print "Error: Zero Ef or Df, pixel not calibrated"
                sys.exit()
            Efe=(0.7317/Df)**2*Ef
            dE=Efe-Ef
            #print i, j, Bank, Pixel, Ef, Df, dE
            ConvertUnits(InputWorkspace=BankTPixel,OutputWorkspace=BankEPixel,EMode='Indirect',Target='DeltaE',EFixed=str(Efe))
            ScaleX(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Factor=str(dE),Operation='Add')

            if ShiftTag==1:
                Rebin(InputWorkspace=BankEPixel,OutputWorkspace='__elastic',Params=IntervalsRebinning(binE),PreserveEvents='0')
                CropWorkspace(InputWorkspace='__elastic',OutputWorkspace='__elastic',XMin='-0.5',XMax='0.5')
                y_data = mtd['__elastic'].readY(0)
                x_data = mtd['__elastic'].readX(0)
                average = 0
                ndata = 0
                for k in range(0,len(y_data)):
                    average += x_data[k]*y_data[k]
                    ndata += y_data[k]
                if ndata != 0:
                    Ave = average/float(ndata)
                else:
                    print 'Error: No data in -0.5<dE<0.5'
                    sys.exit()
                if abs(Ave)>0.5:
                    print 'Warning: Elastic line shift greater than 0.5 meV'
                ScaleX(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Factor=str(-Ave),Operation='Add')

            Rebin(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Params=IntervalsRebinning(binE),PreserveEvents='0')

            if j==0:
                CloneWorkspace(InputWorkspace=BankEPixel,OutputWorkspace=BanksE[i])
            else:
                ConjoinWorkspaces(InputWorkspace1=BanksE[i],InputWorkSpace2=BankEPixel)
        SumSpectra(InputWorkspace=BanksE[i],OutputWorkspace=BanksEsum[i])
        ConvertToDistribution(BanksEsum[i])
        CorrectKiKf(InputWorkspace=BanksEsum[i],OutputWorkspace=BanksEsum[i],EMode='Indirect',EFixed='3.5')

    for i,Bank in enumerate(Banks):
        if Bank==BanksForward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='Forward')
        elif Bank==BanksBackward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='Backward')
        elif Bank in BanksForward:
            AppendSpectra(InputWorkspace1='Forward',InputWorkspace2=BanksEsum[i],OutputWorkspace='Forward')
        elif Bank in BanksBackward:
            AppendSpectra(InputWorkspace1='Backward',InputWorkspace2=BanksEsum[i],OutputWorkspace='Backward')
        else:
            print "Error: Unknown bank, check BankVersion"
            sys.exit()

    SumSpectra(InputWorkspace='Forward',OutputWorkspace='__forward')
    SumSpectra(InputWorkspace='Backward',OutputWorkspace='__backward')
    Scale(InputWorkspace='__forward',OutputWorkspace='__forward',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__backward',OutputWorkspace='__backward',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')

    if ShiftTag==1:
        for WS in ['__backward','__forward']:
            CropWorkspace(InputWorkspace=WS,OutputWorkspace='__elastic',XMin='-0.5',XMax='0.5')
            x_data = mtd['__elastic'].readX(0)
            y_data = mtd['__elastic'].readY(0)
            Height = max(y_data)
            Peak = 0.5*(x_data[y_data.argmax()]+x_data[y_data.argmax()+1])
            ScaleX(InputWorkspace=WS,OutputWorkspace=WS,Factor=str(-Peak),Operation='Add')
            Rebin(InputWorkspace=WS,OutputWorkspace=WS,Params=IntervalsRebinning(binE),PreserveEvents='0')

    if ScaleTag==1:
        factors=[0.99+x*0.001 for x in range(21)]
        cc=[]
        for scale in factors:
            ScaleX(InputWorkspace='__forward',OutputWorkspace='__forward-scaled',Factor=scale,Operation='Multiply')
            RebinToWorkspace(WorkspaceToRebin='__forward-scaled',WorkspaceToMatch='__backward',OutputWorkspace='__forward-scaled')
            x0 = mtd['__backward'].extractX()
            y0 = mtd['__backward'].extractY()
            x1 = mtd['__forward-scaled'].extractX()
            y1 = mtd['__forward-scaled'].extractY()
            yy0=[]
            yy1=[]
            for i in range(len(y0[0])):
                if x0[0][i]>=ScaleXMin and x0[0][i]<=ScaleXMax:
                    yy0.append(y0[0][i])
            for i in range(len(y1[0])):
                if x1[0][i]>=ScaleXMin and x1[0][i]<=ScaleXMax:
                    yy1.append(y1[0][i])
            cc.append(pearson(yy0,yy1))
        imax=cc.index(max(cc))
        if imax==0:
            print 'Warning: Reduce lower bound for scaling'
            sys.exit()
        elif imax==len(cc)-1:
            print 'Warning: Increase upper bound for scaling'
            sys.exit()
        else:
            ScaleX(InputWorkspace='__forward',OutputWorkspace='__forward-scaled',Factor=factors[imax],Operation='Multiply')
            RebinToWorkspace(WorkspaceToRebin='__forward-scaled',WorkspaceToMatch='__backward',OutputWorkspace='__forward')

    AppendSpectra(InputWorkspace1='__backward',InputWorkspace2='__forward',OutputWorkspace='Merged')

    return 'Backward','Forward','Merged'


######################################################################

MonitorT,MonitorE,Prefactor,SampleE=LoadMonitor(binE)
BanksT=LoadInelasticBanks()    
Backward,Forward,Merged=ReduceINS(BanksT,ListPX,CalTab,binE)

Title = mtd['Merged'].getTitle()
Note = Title.split('>')[0]
Note = Note.replace(' ','-')

INS='VIS_'+run_number+'_'+Note
Divide(LHSWorkspace=Merged,RHSWorkspace=SampleE,OutputWorkspace=INS)
Scale(InputWorkspace=INS,OutputWorkspace=INS,Factor='500',Operation='Multiply')
mtd[INS].setYUnitLabel('Normalized intensity')

for ws in BanksT:
    DeleteWorkspace(ws)

RemoveLogs(INS)
SaveNexusProcessed(InputWorkspace=INS,Filename=INS+".nxs")

#if not os.path.exists(SaveDirectory+'/Wavenumber'):
#    os.makedirs(SaveDirectory+'/Wavenumber')
#    print "Info: Subfolder ./Wavenumber does not exist and is created."

#ConvertUnits(InputWorkspace=INS,OutputWorkspace=INS+'-inWavenumber',Target='DeltaE_inWavenumber',EMode='Indirect',EFixed='3.5')
#RemoveLogs(INS+'-inWavenumber')
#OutFile='Wavenumber/VIS_'+run_number+'_'+Note+'_inWavenumber'
#SaveNexusProcessed(InputWorkspace=INS+'-inWavenumber',Filename=OutFile+".nxs")
