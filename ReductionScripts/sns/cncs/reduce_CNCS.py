#!/usr/bin/env python

import os, sys, traceback
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from string import *
from numpy import *
from ARLibrary import * #note that ARLibrary would set mantidpath as well

import sys,os
sys.path.append("/opt/mantid34/bin")
from mantid.simpleapi import *

from matplotlib import *
use("agg")
from matplotlib.pyplot import *
 
#os.remove('/SNS/CNCS/IPTS-11820/shared/autoreduce/van101708.nxs')

import numpy as np
def GetT0FromDet(ws):
    minAngle=40.
    maxAngle=90.
    alpha=437.37 #v=alpha*sqrt(Ei)
    __tempws=CloneWorkspace(ws)
    MaskBTP(__tempws,Bank="35-50")
    MaskBTP(__tempws,Pixel="1-8,121-128")
    MaskAngle(__tempws,0,minAngle)
    MaskAngle(__tempws,maxAngle,180)
    __sumws=SumSpectra(__tempws)
    __sumws=Rebin(__sumws,10,PreserveEvents="1")
    detIDs=__sumws.getSpectrum(0).getDetectorIDs()
    inst=__sumws.getInstrument()
    sample=inst.getSample()
    distances=[inst.getDetector(i).getDistance(sample) for i in detIDs]
    d=np.array(distances).mean()+sample.getDistance(inst.getSource())
    tofs=0.5*(__sumws.readX(0)[:-1]+__sumws.readX(0)[1:])
    ints=__sumws.readY(0)
    #restrict the range to use only elastic line
    length=len(tofs)
    tofs=tofs[int(length*.45):int(length*.55)]
    ints=ints[int(length*.45):int(length*.55)]
    #print tofs
    TOF=tofs[ints.argmax()]
    #TOF=(tofs*ints*ints).sum()/(ints*ints).sum()
    Ei=__sumws.run()['EnergyRequest'].timeAverageValue()
    T0=TOF-1e6*d/alpha/np.sqrt(Ei)
    DeleteWorkspace(__sumws)
    DeleteWorkspace(__tempws)
    return T0

def preprocessVanadium(Raw,Processed,Parameters):
    if os.path.isfile(Processed):
        LoadNexus(Filename=Processed,OutputWorkspace="__VAN")
        dictvan={'UseProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN'}
    else:
        LoadEventNexus(Filename=Raw,OutputWorkspace="__VAN",Precount=0)
        #ChangeBinOffset(InputWorkspace="__VAN",OutputWorkspace="__VAN",Offset=500,IndexMin=54272,IndexMax=55295) # adjust time for pack C17 wired backward
        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        dictvan={'SaveProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN','SaveProcDetVanFilename':Processed}
    return dictvan


config['default.facility']="SNS"
nexus_file=sys.argv[1]
output_directory=sys.argv[2]

seterr("ignore") #ignore division by 0 warning in plots

RawVanadium="/SNS/CNCS/IPTS-4654/25/137573/NeXus/CNCS_137573_event.nxs"
#RawVanadium="/SNS/CNCS/IPTS-4654/24/123012/NeXus/CNCS_123012_event.nxs"
#RawVanadium="/SNS/CNCS/IPTS-13623/0/115557/NeXus/CNCS_115557_event.nxs"
#RawVanadium="/SNS/CNCS/IPTS-4654/23/109039/NeXus/CNCS_109039_event.nxs"
#RawVanadium="/SNS/CNCS/IPTS-4654/22/101708/NeXus/CNCS_101708_event.nxs"
#ProcessedVanadium="van101708both.nxs"
#ProcessedVanadium="van123012.nxs"
ProcessedVanadium="vanadium.nxs"
HardMaskFile=''
IntegrationRange=[49500.0,50500.0]#integration range for Vanadium in TOF

MaskBTPParameters=[{'Pixel':"1-8,121-128"}]
#MaskBTPParameters.append({'Tube': '7,8', 'Bank': '50'})
#MaskBTPParameters.append({'Bank': '37-50'})

w=Load(nexus_file)
EGuess=w.getRun()['EnergyRequest'].firstValue()

tib=SuggestTibCNCS(EGuess)
#if (abs(EGuess-12)<0.1):
#    tib=[20500.0,21500.0]
#tib=[24000,29000]

t0=GetT0FromDet(w)

DGSdict=preprocessVanadium(RawVanadium,output_directory+ProcessedVanadium,MaskBTPParameters)
DGSdict['SampleInputFile']=nexus_file
DGSdict['EnergyTransferRange']=[-0.95*EGuess,0.005*EGuess,0.95*EGuess]  #Typical values are -0.5*EGuess, 0.005*EGuess, 0.95*EGuess
DGSdict['HardMaskFile']=HardMaskFile
DGSdict['GroupingFile']="/SNS/CNCS/shared/autoreduce/CNCS_8x1.xml"
DGSdict['IncidentBeamNormalisation']='ByCurrent'  
DGSdict['UseBoundsForDetVan']='1'
DGSdict['DetVanIntRangeHigh']=IntegrationRange[1]
DGSdict['DetVanIntRangeLow']=IntegrationRange[0]
DGSdict['DetVanIntRangeUnits']='TOF'
DGSdict['OutputWorkspace']='reduce'
DGSdict['TibTofRangeStart']=tib[0]
DGSdict['TibTofRangeEnd']=tib[1]
DGSdict['TimeIndepBackgroundSub']=True
#DGSdict['TimeIndepBackgroundSub']=False

DgsReduction(**DGSdict)
NormalizedVanadiumEqualToOne = True
if DGSdict.has_key('SaveProcessedDetVan') and NormalizedVanadiumEqualToOne:
    filename=DGSdict['SaveProcDetVanFilename']
    LoadNexus(Filename=filename,OutputWorkspace="__VAN")
    datay = mtd['__VAN'].extractY()
    meanval = float(datay[datay>0].mean())
    CreateSingleValuedWorkspace(OutputWorkspace='__meanval',DataValue=meanval)
    Divide(LHSWorkspace='__VAN',RHSWorkspace='__meanval',OutputWorkspace='__VAN') #Divide the vanadium by the mean
    Multiply(LHSWorkspace='reduce',RHSWorkspace='__meanval',OutputWorkspace='reduce') #multiple by the mean of vanadium Normalized data = Data / (Van/meanvan) = Data *meanvan/Van
    SaveNexus(InputWorkspace="__VAN", Filename= filename) 

filename=output_directory+ProcessedVanadium
os.chmod(filename,0444)

filename = os.path.split(nexus_file)[-1]
#run_number = filename.split('_')[1]

#added Feb 10, 2014 AS GE
elog=ExperimentLog()
elog.setLogList('Speed1,Phase1,Speed2,Phase2,Speed3,Phase3,Speed4,Phase4,Speed5,Phase5,EnergyRequest')
elog.setSimpleLogList("EnergyRequest")
#elog.setSERotOptions('Ox2WeldRot')
elog.setSERotOptions('SERotator2')
#elog.setSERotOptions('ThreeSampleRot')
#elog.setSERotOptions('SERotator2,OxDilRot,CCR13VRot,FatSamVRot,SEOCRot,huber,CCR10G2Rot')
#elog.setSETempOptions('SampleTemp,sampletemp,SensorC,SensorB,SensorA')
elog.setSETempOptions('SensorB')
elog.setFilename(output_directory+'experiment_log.csv')

s1=elog.save_line('reduce')

# Get Angle
s1=mtd["reduce"].getRun()['SERotator2'].value[0]
#s1=mtd["reduce"].getRun()['ThreeSampleRot'].value[0]
roundedvalue = "%.1f" % s1
valuestringwithoutdot = str(roundedvalue).replace('.', 'p')

run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
processed_filename = os.path.join(output_directory, "CNCS_" + run_number + "_" + valuestringwithoutdot + "_spe.nxs")
nxspe_filename=os.path.join(output_directory, "CNCS_" + run_number + "_" + valuestringwithoutdot + ".nxspe")

# Save a file
SaveNexus(Filename=processed_filename, InputWorkspace="reduce")
SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce", Psi=str(s1), KiOverKfScaling='1')
os.chmod(nxspe_filename,0664)
# make a pretty image
#minvals,maxvals=ConvertToMDMinMaxGlobal('reduce','|Q|','Direct')
#xmin=minvals[0]
#xmax=maxvals[0]
#xstep=(xmax-xmin)*0.01
#ymin=minvals[1]
#ymax=maxvals[1]
#ystep=(ymax-ymin)*0.01
#x=arange(xmin,xmax,xstep)
#y=arange(ymin,ymax,ystep)
#X,Y=meshgrid(x,y)


#MD=ConvertToMD('reduce',QDimensions='|Q|',dEAnalysisMode='Direct',MinValues=minvals,MaxValues=maxvals)
#ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
#ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
#MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
#d=MDH.getSignalArray()
#ne=MDH.getNumEventsArray()
#dne=d/ne

#Zm=ma.masked_where(ne==0,dne)
#pcolormesh(X,Y,log(Zm),shading='gouraud')
#xlabel('|Q| ($\AA^{-1}$)')
#ylabel('E (meV)')
#savefig(processed_filename+'.png',bbox_inches='tight')

