######################################################################
# Python script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv
import string

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
    RunNumber = FileName.strip('VIS_').replace('.nxs.h5','')
    ListRN = [int(RunNumber)]
    SaveDir = sys.argv[2]
    config['defaultsave.directory'] = SaveDir
elif Interface == 1:
    IPTS='IPTS-11661'
    ListRN=[4979,4980,4981]
    Note='Cu-MFU4L-1g-5K'
    SaveDir='/SNS/VIS/shared/VIS_team/2014-B'
    config['defaultsave.directory'] = SaveDir
    Root='/SNS/VIS/'+IPTS+'/nexus'  
    config.setDataSearchDirs(Root) 

#*********************************************************************
# Save processed nxs file?
# 0: No. 1: Yes
SaveNexus = 1
#*********************************************************************

#*********************************************************************
# At which level the spectrum will be normalized?
# 0: Overall. 1: pixel-by-pixel level
# Note: 0 is faster but 1 is required for Bragg-edge correction
NormLevel = 1
#*********************************************************************

#*********************************************************************
# Where to find monitor data?
# 0: load from current nxs files. 1: load from other nxs files. 
# 2: open pre-processed/corrected normalization histogram
GetMon = 2
#*********************************************************************
if GetMon == 0:
    IPTSBM = IPTS
    ListBM = ListRN
elif GetMon == 1:
    IPTSBM = 'IPTS-9917'
    ListBM = [4888,4889,4890]
elif GetMon == 2:
    # If NormLevel=0, a monitor spectrum in energy transfer is needed
    # If NormLevel=1, a monitor spectrum in wavelength is needed
    MonFile = '/SNS/VIS/shared/VIS_team/VIS_reduction/VIS_4946-4951_MonitorL-corrected.nxs'

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
# Shift the spectrum to further align the elastic lines?
# 0: No. 1: Yes
ShiftSpec = 0
#*********************************************************************

#*********************************************************************
# Scale the forward spectrum to align with the backward spectrum?
# 0: No. 1: Yes
ScaleSpec = 0
#*********************************************************************
if ScaleSpec == 1:
    ScaleXMin=50
    ScaleXMax=500

#*********************************************************************
# Binning parameters
binE='-2,0.005,5,-0.001,1000'
binL='0.28,0.001,8.2'
#*********************************************************************

#*********************************************************************
# Banks to be used
BanksForward=[2,3,4,5,6]
BanksBackward=[8,9,10,11,12,13,14]
Banks=BanksForward+BanksBackward
#*********************************************************************

#*********************************************************************
# How would you like the the pixels to be selected
# 0: static. 1: dynamic
PixSel = 0
#*********************************************************************
ListPX = []
if PixSel == 0:
    PXs=range(2*128+48,2*128+80)+  \
        range(3*128+32,3*128+96)+  \
        range(4*128+32,4*128+96)+  \
        range(5*128+48,5*128+80)
    for _ in Banks:
        ListPX.append(PXs)
else:
    TolMax = 0.5

#*********************************************************************
# Calibration table
CalFile='/SNS/VIS/shared/VIS_team/VIS_reduction/VIS_CalTab-03-03-2014.csv'
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

def FindMonSpec(RunNum,yvalues,MonID):

    mlst = []  
    for i in range(len(yvalues)):
        mlst.append(yvalues[i][0])
    iMax = mlst.index(max(mlst))
    if MonID > 1:
        mlst[iMax] = 0
        iMax=mlst.index(max(mlst))
    return iMax


######################################################################
# Load monitor data
######################################################################

def LoadMonitor(IPTSBM,ListBM,MonID):
    
    for RunNum in ListBM:
        FileName = '/SNS/VIS/'+IPTSBM+'/nexus/VIS_'+str(RunNum)+'.nxs.h5'
        print 'Loading monitor data from', FileName
        if RunNum==ListBM[0]:
            LoadNexusMonitors(Filename=FileName,OutputWorkspace='__monitor')
            yvalues = mtd['__monitor'].extractY()
            iSpec = FindMonSpec(RunNum,yvalues,MonID)
            ExtractSingleSpectrum(InputWorkspace='__monitor',OutputWorkspace='MonitorT',WorkspaceIndex=str(iSpec))
        else:
            LoadNexusMonitors(Filename=FileName,OutputWorkspace='__monitor')
            yvalues = mtd['__monitor'].extractY()
            iSpec = FindMonSpec(RunNum,yvalues,MonID)
            ExtractSingleSpectrum(InputWorkspace='__monitor',OutputWorkspace='__add',WorkspaceIndex=str(iSpec))
            Plus(LHSWorkspace='MonitorT',RHSWorkspace='__add',OutputWorkspace='MonitorT')
    
    if mtd['MonitorT'].getRun().getProtonCharge() < 1.0e-5:
        print "Error: Proton charge is too low"
        sys.exit()
    print 'Processing monitor data'
    NormaliseByCurrent(InputWorkspace='MonitorT',OutputWorkspace='MonitorT')
    RemoveArtifact('MonitorT',100,33333,16660,12)

    return 'MonitorT'


######################################################################
# Load inelastic banks
######################################################################

def LoadInelasticBanks(ListRN,Banks):
    
    BanksT = []
    for BankNum in Banks:
        BanksT.append('BankT_'+str(BankNum))
    for RunNum in ListRN:
        FileName = 'VIS_'+str(RunNum)+'.nxs.h5'
        print 'Loading inelastic banks from', FileName
        if RunNum==ListRN[0]:
            for i,BankNum in enumerate(Banks):
                BankLoad='bank'+str(BankNum)
                LoadEventNexus(Filename=FileName,OutputWorkspace=BanksT[i],SingleBankPixelsOnly=True,BankName=BankLoad,CompressTolerance='-1',FilterByTofMin=100,FilterByTofMax=33333,LoadLogs='1')
                #ModeratorTzero(InputWorkspace=BanksT[i],OutputWorkspace=BanksT[i])
                print "Title:", mtd[BanksT[i]].getTitle()
                print "Proton charge:", mtd[BanksT[i]].getRun().getProtonCharge()
                if "Temperature Adjustment" in mtd[BanksT[i]].getTitle():
                    print "Error: Non-equilibrium runs will not be reduced"
                    sys.exit()
                if mtd[BanksT[i]].getRun().getProtonCharge() < 50.0:
                    print "Error: Proton charge is too low"
                    sys.exit()
        else:
            for i,BankNum in enumerate(Banks):
                BankLoad='bank'+str(BankNum)
                LoadEventNexus(Filename=FileName,OutputWorkspace='__add',SingleBankPixelsOnly=True,BankName=BankLoad,CompressTolerance='-1',FilterByTofMin=100,FilterByTofMax=33333,LoadLogs='1')
                #ModeratorTzero(InputWorkspace='__add',OutputWorkspace='__add')
                Plus(LHSWorkspace=BanksT[i],RHSWorkspace='__add',OutputWorkspace=BanksT[i])
    for i,BankNum in enumerate(Banks):
        if mtd[BanksT[i]].getRun().getProtonCharge() < 1.0e-5:
            print "Error: Proton charge is too low"
            sys.exit()
        print 'Processing data in Bank #', Banks[i]
        NormaliseByCurrent(InputWorkspace=BanksT[i],OutputWorkspace=BanksT[i])
        RemoveArtifact(BanksT[i],100,33333,16660,240)

    return BanksT



######################################################################
# Correct monitor spectrum for normalization
######################################################################

def CorrectMonitor(Monitor,Attenuator,NormLevel):

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
            ym = ym*numpy.exp(0.0*sigma_vol*thickness)
        yvalues[0][i]=ym
        evalues[0][i]=0
    Prefactor=CreateWorkspace(DataX=xvalues,DataY=yvalues,DataE=evalues,NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=Monitor,RHSWorkspace=Prefactor,OutputWorkspace=Monitor+'-corrected')

    return Monitor+'-corrected'


######################################################################
# Move the center of mass to zero (elastic line)
######################################################################

def AlignCOM(WS,binE):
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__elastic',XMin='-0.5',XMax='0.5')
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
    ScaleX(InputWorkspace=WS,OutputWorkspace=WS,Factor=str(-Ave),Operation='Add')
    Rebin(InputWorkspace=WS,OutputWorkspace=WS,Params=binE,PreserveEvents='1')

######################################################################
# Move the maximum point to zero (elastic line)
######################################################################

def AlignMAX(WS,binE):
    CropWorkspace(InputWorkspace=WS,OutputWorkspace='__elastic',XMin='-0.5',XMax='0.5')
    x_data = mtd['__elastic'].readX(0)
    y_data = mtd['__elastic'].readY(0)
    Height = max(y_data)
    Peak = 0.5*(x_data[y_data.argmax()]+x_data[y_data.argmax()+1])
    ScaleX(InputWorkspace=WS,OutputWorkspace=WS,Factor=str(-Peak),Operation='Add')
    Rebin(InputWorkspace=WS,OutputWorkspace=WS,Params=binE,PreserveEvents='1')

######################################################################
# Align forward spectrum to backward spectrum
######################################################################

def AlignBF(WSB,WSF,ScaleXMin,ScaleXMax):
    factors=[0.99+x*0.001 for x in range(21)]
    cc=[]
    for scale in factors:
        ScaleX(InputWorkspace=WSF,OutputWorkspace=WSF+'-scaled',Factor=scale,Operation='Multiply')
        RebinToWorkspace(WorkspaceToRebin=WSF+'-scaled',WorkspaceToMatch=WSB,OutputWorkspace=WSF+'-scaled')
        x0 = mtd[WSB].extractX()
        y0 = mtd[WSB].extractY()
        x1 = mtd[WSF+'-scaled'].extractX()
        y1 = mtd[WSF+'-scaled'].extractY()
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
        ScaleX(InputWorkspace=WSF,OutputWorkspace=WSF,Factor=factors[imax],Operation='Multiply')
        RebinToWorkspace(WorkspaceToRebin=WSF,WorkspaceToMatch=WSB,OutputWorkspace=WSF)


######################################################################
# Convert from distribution (single spectrum only)
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
    Prefactor=CreateWorkspace(DataX=xvalues[0],DataY=yvalues[0],DataE=evalues[0],NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=WS,RHSWorkspace=Prefactor,OutputWorkspace=WS)

######################################################################
# Convert to distribution (single spectrum only)
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
    Prefactor=CreateWorkspace(DataX=xvalues[0],DataY=yvalues[0],DataE=evalues[0],NSpec=1,UnitX=xunit,YUnitLabel=yunitlabel)
    Multiply(LHSWorkspace=WS,RHSWorkspace=Prefactor,OutputWorkspace=WS)


######################################################################
# Dynamically select pixels to be included in reduction
######################################################################

def DynPixSel(BanksT,Banks,TolMax):

    ListPX = []
    print "Pixels selected dynamically with TolMax=",TolMax
    for i, Bank in enumerate(BanksT):
        Rebin(InputWorkspace=Bank,OutputWorkspace='__binned',Params='100,10,33333',PreserveEvents='1')
        Integration(InputWorkspace='__binned',OutputWorkspace='__INT',RangeLower='100',RangeUpper='33333')
        Integral = []
        for j in range(1024):
            Integral.append(mtd['__INT'].readY(j)[0])
        Maximum = max(Integral)
        PXs = []
        for j in range(1024):
            if Integral[j] > TolMax*Maximum:
	        PXs.append(j)
        ListPX.append(PXs)
        print len(PXs)," pixels selected in Bank #",Banks[i]

    return ListPX


######################################################################
# Inelastic data reduction (pixel level, normalization in wavelength)
######################################################################

def ReducePixelsL(NormL,BanksT,Banks,BanksForward,BanksBackward,ListPX,CalTab,binE):

    BanksL=[]
    BanksLnorm=[]
    BanksE=[]
    BanksLsum=[]
    BanksLnormsum=[]
    BanksEsum=[]
    for i, Bank in enumerate(BanksT):    
        print 'Reducing data in Bank #', Banks[i]
        BanksL.append('__BankL_'+str(Banks[i]))
        BanksLnorm.append('__BankLnorm_'+str(Banks[i]))
        BanksE.append('__BankE_'+str(Banks[i]))
        BanksLsum.append('BankL_'+str(Banks[i])+'_sum')
        BanksLnormsum.append('BankLnorm_'+str(Banks[i])+'_sum')
        BanksEsum.append('BankE_'+str(Banks[i])+'_sum')
        for j,Pixel in enumerate(ListPX[i]):
            BankTPixel='__bankT_pixel'
            BankLPixel='__bankL_pixel'
            ExtractSingleSpectrum(InputWorkspace=Bank,OutputWorkspace=BankTPixel,WorkspaceIndex=str(Pixel))
            Ef=CalTab[Banks[i]-1][Pixel][0]
            Df=CalTab[Banks[i]-1][Pixel][1]
            if Ef==0 or Df==0:
                print "Error: Zero Ef or Df, pixel not calibrated"
                sys.exit()
            Efe=(0.7317/Df)**2*Ef
            ConvertUnits(InputWorkspace=BankTPixel,OutputWorkspace=BankLPixel,EMode='Indirect',Target='Wavelength',EFixed=str(Efe))
            if j==0:
                CloneWorkspace(InputWorkspace=BankLPixel,OutputWorkspace=BanksL[i])
            else:
                ConjoinWorkspaces(InputWorkspace1=BanksL[i],InputWorkSpace2=BankLPixel)	    
	    
        RebinToWorkspace(WorkspaceToRebin=BanksL[i],WorkspaceToMatch=NormL,OutputWorkspace=BanksL[i],PreserveEvents='1')
        ConvertToDist(BanksL[i])
        Divide(LHSWorkspace=BanksL[i],RHSWorkspace=NormL,OutputWorkspace=BanksLnorm[i])
	    
        for j,Pixel in enumerate(ListPX[i]):
            BankLPixel='__bankL_pixel'
            BankEPixel='__bankE_pixel'
            ExtractSingleSpectrum(InputWorkspace=BanksLnorm[i],OutputWorkspace=BankLPixel,WorkspaceIndex=str(j))
            Ef=CalTab[Banks[i]-1][Pixel][0]
            ConvertUnits(InputWorkspace=BankLPixel,OutputWorkspace=BankEPixel,EMode='Indirect',Target='DeltaE',EFixed=str(Ef))
            ConvertFromDist(BankEPixel)
            Rebin(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Params=binE,PreserveEvents='1')
            if ShiftSpec==1:
                AlignCOM(BankEPixel,binE)
            if j==0:
                CloneWorkspace(InputWorkspace=BankEPixel,OutputWorkspace=BanksE[i])
            else:
                ConjoinWorkspaces(InputWorkspace1=BanksE[i],InputWorkSpace2=BankEPixel)

        SumSpectra(InputWorkspace=BanksL[i],OutputWorkspace=BanksLsum[i])
        SumSpectra(InputWorkspace=BanksLnorm[i],OutputWorkspace=BanksLnormsum[i])
        SumSpectra(InputWorkspace=BanksE[i],OutputWorkspace=BanksEsum[i])


    for i,Bank in enumerate(Banks):
        if Bank==BanksForward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='__ForwardE')
        elif Bank==BanksBackward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='__BackwardE')
        elif Bank in BanksForward:
            AppendSpectra(InputWorkspace1='__ForwardE',InputWorkspace2=BanksEsum[i],OutputWorkspace='__ForwardE')
        elif Bank in BanksBackward:
            AppendSpectra(InputWorkspace1='__BackwardE',InputWorkspace2=BanksEsum[i],OutputWorkspace='__BackwardE')
        else:
            print "Error: Unknown bank, check BankVersion"
            sys.exit()

    SumSpectra(InputWorkspace='__ForwardE',OutputWorkspace='__ForwardE-sum')
    SumSpectra(InputWorkspace='__BackwardE',OutputWorkspace='__BackwardE-sum')
    Scale(InputWorkspace='__ForwardE-sum',OutputWorkspace='__ForwardE-sum',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__BackwardE-sum',OutputWorkspace='__BackwardE-sum',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')

    if ShiftSpec==1:
        for WS in ['__BackwardE-sum','__ForwardE-sum']:
            AlignMAX(WS,binE)

    if ScaleSpec==1:
        AlignBF('__BackwardE-sum','__ForwardE-sum',ScaleXMin,ScaleXMax)

    AppendSpectra(InputWorkspace1='__BackwardE-sum',InputWorkspace2='__ForwardE-sum',OutputWorkspace='MergedE')
    ConvertToMatrixWorkspace(InputWorkspace='MergedE',OutputWorkspace='MergedE')
    ConvertToDistribution('MergedE')
    CorrectKiKf(InputWorkspace='MergedE',OutputWorkspace='MergedE',EMode='Indirect',EFixed='3.5')

    return 'MergedE'


######################################################################
# Inelastic data reduction (normalization in deltaE)
######################################################################

def ReduceBanksE(NormE,BanksT,Banks,BanksForward,BanksBackward,ListPX,CalTab,binE):

    BanksE=[]
    BanksEsum=[]
    for i, Bank in enumerate(BanksT):
        print 'Reducing data in Bank #', Banks[i]
        BanksE.append('__BankE_'+str(Banks[i]))
        BanksEsum.append('__BankEsum_'+str(Banks[i]))
        for j,Pixel in enumerate(ListPX[i]):
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
            ConvertUnits(InputWorkspace=BankTPixel,OutputWorkspace=BankEPixel,EMode='Indirect',Target='DeltaE',EFixed=str(Efe))
            ScaleX(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Factor=str(dE),Operation='Add')
            Rebin(InputWorkspace=BankEPixel,OutputWorkspace=BankEPixel,Params=binE,PreserveEvents='1')
            if ShiftSpec==1:
                AlignCOM(BankEPixel,binE)
            if j==0:
                CloneWorkspace(InputWorkspace=BankEPixel,OutputWorkspace=BanksE[i])
            else:
                ConjoinWorkspaces(InputWorkspace1=BanksE[i],InputWorkSpace2=BankEPixel)

        SumSpectra(InputWorkspace=BanksE[i],OutputWorkspace=BanksEsum[i])

    for i,Bank in enumerate(Banks):
        if Bank==BanksForward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='__Forward')
        elif Bank==BanksBackward[0]:
            CloneWorkspace(InputWorkspace=BanksEsum[i],OutputWorkspace='__Backward')
        elif Bank in BanksForward:
            AppendSpectra(InputWorkspace1='__Forward',InputWorkspace2=BanksEsum[i],OutputWorkspace='__Forward')
        elif Bank in BanksBackward:
            AppendSpectra(InputWorkspace1='__Backward',InputWorkspace2=BanksEsum[i],OutputWorkspace='__Backward')
        else:
            print "Error: Unknown bank, check BankVersion"
            sys.exit()

    SumSpectra(InputWorkspace='__Forward',OutputWorkspace='__Forward-sum')
    SumSpectra(InputWorkspace='__Backward',OutputWorkspace='__Backward-sum')
    Scale(InputWorkspace='__Forward-sum',OutputWorkspace='__Forward-sum',Factor=str(1.0/len(BanksForward)),Operation='Multiply')
    Scale(InputWorkspace='__Backward-sum',OutputWorkspace='__Backward-sum',Factor=str(1.0/len(BanksBackward)),Operation='Multiply')

    if ShiftSpec==1:
        for WS in ['__Backward-sum','__Forward-sum']:
            AlignMAX(WS,binE)

    if ScaleSpec==1:
        AlignBF('__Backward-sum','__Forward-sum',ScaleXMin,ScaleXMax)

    AppendSpectra(InputWorkspace1='__Backward-sum',InputWorkspace2='__Forward-sum',OutputWorkspace='MergedE')
    RebinToWorkspace(WorkspaceToRebin='MergedE',WorkspaceToMatch=NormE,OutputWorkspace='MergedE',PreserveEvents='0')
    ConvertToMatrixWorkspace(InputWorkspace='MergedE',OutputWorkspace='MergedE')
    ConvertToDistribution('MergedE')
    CorrectKiKf(InputWorkspace='MergedE',OutputWorkspace='MergedE',EMode='Indirect',EFixed='3.5')
    Divide(LHSWorkspace='MergedE',RHSWorkspace=NormE,OutputWorkspace='MergedE')

    return 'MergedE'




######################################################################
# Main program
######################################################################

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

BanksT=LoadInelasticBanks(ListRN,Banks) 
if PixSel == 1:
    ListPX=DynPixSel(BanksT,Banks,TolMax)

if NormLevel == 0:
    if GetMon == 0 or GetMon == 1:
        MonitorT=LoadMonitor(IPTSBM,ListBM,MonID)
        ConvertUnits(InputWorkspace=MonitorT,OutputWorkspace='MonitorE',Target='Energy')
        ConvertUnits(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Target='DeltaE',EMode='Indirect',EFixed='3.5')
        ScaleX(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Factor='-3.5',Operation='Add')
        Rebin(InputWorkspace='MonitorE',OutputWorkspace='MonitorE',Params=binE,PreserveEvents='0')
        NormE = CorrectMonitor('MonitorE',Attenuator,NormLevel)
        ConvertToDistribution(Workspace=NormE)
        SmoothData(InputWorkspace=NormE,OutputWorkspace=NormE,NPoints='201')
    elif GetMon == 2:
        LoadNexusProcessed(Filename=MonFile,OutputWorkspace='SavedMonitor',LoadHistory=False)
        NormE = 'SavedMonitor'
    MergedE = ReduceBanksE(NormE,BanksT,Banks,BanksForward,BanksBackward,ListPX,CalTab,binE)

elif NormLevel == 1:
    if GetMon == 0 or GetMon ==1:
        MonitorT=LoadMonitor(IPTSBM,ListBM,MonID)
        ConvertUnits(InputWorkspace=MonitorT,OutputWorkspace='MonitorL',Target='Wavelength')
        Rebin(InputWorkspace='MonitorL',OutputWorkspace='MonitorL',Params=binL,PreserveEvents='0')
        NormL = CorrectMonitor('MonitorL',Attenuator,NormLevel)
        ConvertToDistribution(Workspace=NormL)
        FFTSmooth(InputWorkspace=NormL,OutputWorkspace=NormL,Filter='Zeroing',Params='20')
    elif GetMon == 2:
        LoadNexusProcessed(Filename=MonFile,OutputWorkspace='SavedMonitor',LoadHistory=False)
        NormL = 'SavedMonitor'
    MergedE = ReducePixelsL(NormL,BanksT,Banks,BanksForward,BanksBackward,ListPX,CalTab,binE)

if Interface == 0:
    Title = mtd[MergedE].getTitle()
    Note = Title.split('>')[0]
    Note = FormatFilename(Note)
    INS = RunNumber+'_'+Note
elif Interface == 1:
    INS = str(ListRN[0])+'-'+str(ListRN[len(ListRN)-1])+'_'+IPTS+'_'+Note

Scale(InputWorkspace=MergedE,OutputWorkspace=INS,Factor='500',Operation='Multiply')
mtd[INS].setYUnitLabel('Normalized intensity')

if SaveNexus==0:
    print "Warning: Reduced data NOT saved."
    sys.exit()

RemoveLogs(INS)
OutFile='VIS_'+INS
SaveNexusProcessed(InputWorkspace=INS,Filename=OutFile+".nxs")

