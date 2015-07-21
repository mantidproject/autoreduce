import sys
import os
import grp
import getpass
import numpy

######################################################################
# Find raw data file with a given run number
######################################################################

def findfiles(RunNum):

    for ipts in os.listdir('/SNS/VIS'):
        rawdir='/SNS/VIS/'+ipts+'/nexus'
        if os.path.exists(rawdir):
            for rawfilename in os.listdir(rawdir):
                if 'VIS_'+str(RunNum) in rawfilename:
                    rawfullname=os.path.join(rawdir, rawfilename)
                    print rawfullname
                    return ipts, rawfilename, rawfullname
    print 'Error: Could not find file(s) for run number '+str(RunNum)
    sys.exit()

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
# Main program
######################################################################
def process_all(ListRN,LoadOption,PixRng,PPulse,Norm,LogTbin,binD,ListTB,TimeStart,TimeStop):

    Pixel=[0,0]
    DiffTube=[]

    Pixel0=14*8*128
    for i in range(0,10):
        Pixel[0]=Pixel0+i*256*8
        Pixel[1]=Pixel0+(i+1)*256*8-1
        for j in range(0,8):
            DiffTube.append([Pixel[0]+j*256,Pixel[0]+(j+1)*256-1])

    if len(ListRN)==1:
        MergedWS='VIS_BSD_'+str(ListRN[0])
    else:
        MergedWS='VIS_BSD_'+str(ListRN[0])+'-'+str(ListRN[len(ListRN)-1])
        
    if Norm==1:
        if LogTbin==0:
            MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorT-hist.nxs'
        elif LogTbin==1:
            MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorTlog-hist.nxs'
        LoadNexusProcessed(Filename=MonFile,OutputWorkspace='Monitor',LoadHistory=False)

    bank_list = ["bank%d" % i for i in range(15, 25)]
    bank_property = ",".join(bank_list)

    for RunNum in ListRN:
        [IPTS,h5FileName,h5FullName]=findfiles(RunNum)
        FileName=h5FileName.strip('.nxs.h5')
        if LoadOption==2:
            break
        elif LoadOption==0 and TimeStop==0:
            LoadEventNexus(Filename=h5FullName, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace=FileName)
        elif LoadOption==0 and TimeStop!=0:
            TStart=TimeStart*60
            TStop=TimeStop*60
            LoadEventNexus(Filename=h5FullName, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace=FileName,FilterByTimeStart=TStart,FilterByTimeStop=TStop)
        elif LoadOption==1:
            SlicedFile='/SNS/VIS/'+IPTS+'/shared/autoreduce/sliced_data/'+FileName+'_elastic_backscattering.nxs.h5'
            if os.path.isfile(SlicedFile):
                Load(Filename=SlicedFile, OutputWorkspace=FileName, LoaderName='LoadNexusProcessed', LoaderVersion=1)
            else:
                print "Error: Sliced data not found. Set LoadSliced=0 to use the original data."
                sys.exit()

        print "Title:", mtd[FileName].getTitle()
        print "Proton charge:", mtd[FileName].getRun().getProtonCharge()
        if "Temperature" in mtd[FileName].getTitle():
            print "Error: Non-equilibrium runs will not be reduced"
            sys.exit()
        if mtd[FileName].getRun().getProtonCharge() < 1.0:
            print "Error: Proton charge is too low"
            sys.exit()

        NormaliseByCurrent(InputWorkspace=FileName,OutputWorkspace=FileName)
        if PPulse==1:
            RemoveArtifact(FileName,10,33333,16662,70)
        if Norm==1:
            RebinToWorkspace(WorkspaceToRebin=FileName, WorkspaceToMatch='Monitor', OutputWorkspace=FileName, PreserveEvents=False)
            Divide(LHSWorkspace=FileName, RHSWorkspace='Monitor', OutputWorkspace=FileName)
        ConvertUnits(InputWorkspace=FileName, OutputWorkspace=FileName, Target='dSpacing')
        Rebin(InputWorkspace=FileName, OutputWorkspace=FileName, Params=binD, PreserveEvents=False)
        if Norm!=1:
            ConvertToDistribution(FileName)
        if RunNum==ListRN[0]:
            CloneWorkspace(InputWorkspace=FileName,OutputWorkspace=MergedWS)
        else:
            WeightedMean(InputWorkspace1=MergedWS,InputWorkspace2=FileName,OutputWorkspace=MergedWS)
        DeleteWorkspace(FileName)

    ListWS=[]
    ListInt=[]

    for i,Tube in enumerate(DiffTube):
        #ListPX=range(Tube[0]+PixRng[0],Tube[0]+PixRng[1])
        #BK=i/8+15
        #TB=i%8+1
        #ListWS.append(MergedWS+'-BK'+str(BK)+'-TB'+str(TB)+'_'+str(PixRng[0])+'-'+str(PixRng[1]))
        #GroupDetectors(InputWorkspace=MergedWS, OutputWorkspace=MergedWS+'-BK'+str(BK)+'-TB'+str(TB)+'_'+str(PixRng[0])+'-'+str(PixRng[1]), DetectorList=ListPX, Behaviour='Average')
        if i+1 in ListTB:
            ListInt+=range(Tube[0]+PixRng[0],Tube[0]+PixRng[1])
    BSD=MergedWS+'_TB'+str(ListTB[0])+'-TB'+str(ListTB[len(ListTB)-1])+'_PX'+str(PixRng[0])+'-PX'+str(PixRng[1])
    GroupDetectors(InputWorkspace=MergedWS, OutputWorkspace=BSD, DetectorList=ListInt, Behaviour='Average')
    #GroupWorkspaces(InputWorkspaces=ListWS,OutputWorkspace=MergedWS+'-Diffraction'+'-'+str(PixRng[0])+'-'+str(PixRng[1]))
    #DeleteWorkspace(MergedWS)
    if Norm==1:
        DeleteWorkspace('Monitor')

    if SaveNexusOutput==0:
        print "Warning: Reduced data NOT saved."
        sys.exit()
    RemoveLogs(BSD)
    RemoveWorkspaceHistory(BSD)
    SaveDir='/SNS/VIS/'+IPTS+'/shared/diffraction'
    if not os.path.exists(SaveDir):
        os.umask(0002)
        os.makedirs(SaveDir,0775)
        gid= grp.getgrnam('users').gr_gid
        os.chown(SaveDir,-1,gid)
        print "Info: "+SaveDir+" does not exist and will be created."
    cmdline='nxdir '+h5FullName+' --data-mode script -p /entry/title'
    f=os.popen(cmdline)
    title = f.read()
    title=title.split('=')[1]
    title='_'.join(title.split()[0:-2])
    username=getpass.getuser()
    if LoadOption==0 and TimeStop!=0 :
        OutFile=os.path.join(SaveDir,BSD+'_'+str(TimeStart)+'-'+str(TimeStop)+'_'+title+'-'+username+'.nxs')
    else:
        OutFile=os.path.join(SaveDir,BSD+'_'+title+'-'+username+'.nxs')
    SaveNexusProcessed(InputWorkspace=BSD,Filename=OutFile)

# Please check/change the following parameters
#=====================================================================
Interface = 0
if Interface == 0:
    sys.path.append("/opt/Mantid/bin")
    from mantid.simpleapi import *
    NexusFile = os.path.abspath(sys.argv[1])
    FileName = NexusFile.split(os.sep)[-1]
    RunNumber = int(FileName.strip('VIS_').replace('.nxs.h5',''))
    ListRN=[RunNumber]
    if len(sys.argv)!=4:
        TimeStart=0
        TimeStop=0
    else:
        TimeStart=int(sys.argv[2])
        TimeStop=int(sys.argv[3])
elif Interface == 1:
    ListRN=[17071]
    TimeStart=0
    TimeStop=0

LoadOption=0   # 0: load original nxs file (BSD only)  1: Load histogramed data  2: Use the already loaded data
PixRng=[128,240]     # Range of pixels to reduce (0-255)
PPulse=0        # 0: no action on the prompt pulse    1: remove prompt pulse 
Norm=1          # 0: no normalization  1: with normalization 
LogTbin=1      # 0: binT='10,1,33333'    1: binT='10,1,2000,-0.0005,33333'
binD='0.02,0.0002,4' # bin parameters in dspace
ListTB=range(2,20) # list of tubes to integrate
# TB01-10(N),TB11-20(N),TB21-30(Y),TB31-40(Y),TB41-50(Y),TB51-60(N),TB61-70(YL),TB71-80(Y)
# BK15: TB01-08, BK16: TB09-16, BK17: TB17-24, BK18: TB25-32, BK19: TB33-40
# BK20: TB41-48, BK21: TB49-56, BK22: TB57-64, BK23: TB65-72, BK24: TB73-80
SaveNexusOutput=1
#=====================================================================
process_all(ListRN,LoadOption,PixRng,PPulse,Norm,LogTbin,binD,ListTB,TimeStart,TimeStop)
