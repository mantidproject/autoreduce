#!/usr/bin/env python
import sys,os,math
sys.path.append("/opt/Mantid/bin")
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from ARLibrary import * #note that ARLibrary would set mantidpath as well
from mantid.simpleapi import *
from matplotlib import *

use("agg")
from matplotlib.pyplot import *
# Logs at: /var/log/SNS_applications/autoreduce.log
import numpy

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
        
def preprocessData(filename):
    f1 = os.path.split(filename)[-1]
    runnum = int(f1.strip('SEQ_').replace('.nxs.h5',''))
    __MonWS=LoadNexusMonitors(Filename=filename)
    #FilterByLogValue("__MonWS",OutputWorkspace="__MonWS",LogName="CCR22Rot",MinimumValue=52.2,MaximumValue=52.4)
    Eguess=__MonWS.getRun()['EnergyRequest'].getStatistics().mean
    ###########################
    #Temporary workaround for IPTS-9145  GEG
    if Eguess<5:
      Eguess=120.
    ###################  
    
    if (runnum >= 46951 and runnum <= 46994):

        Efixed = 119.37
        T0 = 25.84

        LoadEventNexus(Filename=filename,OutputWorkspace="__IWS",Precount=0) #Load an event Nexus file
        #Fix that all time series log values start at the same time as the proton_charge
        CorrectLogTimes('__IWS')

        #Filter chopper 3 bad events
        valC3=__MonWS.getRun()['Phase3'].getStatistics().median

        MaskBTP(workspace='__IWS', Bank='38-57,75-94')

        return [Eguess,Efixed,T0]
    
    try:   
             sp1=-1
             sp2=-1
             nsp=__MonWS.getNumberHistograms()                
             if nsp < 2:
                 raise ValueError("There are less than 2 monitors")
             for sp in range(nsp):
                 if __MonWS.getSpectrum(sp).getDetectorIDs()[0]==-1:
                     sp1=sp
                 if __MonWS.getSpectrum(sp).getDetectorIDs()[0]==-2:
                     sp2=sp
             if sp1==-1:
                 raise RuntimeError("Could not find spectrum for the first monitor")
             if sp2==-1:
                 raise RuntimeError("Could not find spectrum for the second monitor")       
             so=__MonWS.getInstrument().getSource().getPos()
             m1=__MonWS.getDetector(sp1).getPos()
             m2=__MonWS.getDetector(sp2).getPos()
             v=437.4*numpy.sqrt(__MonWS.getRun()['EnergyRequest'].getStatistics().mean)
             t1=m1.distance(so)*1e6/v
             t2=m2.distance(so)*1e6/v
             t1f=int(t1*60e-6) #frame number for monitor 1
             t2f=int(t2*60e-6) #frame number for monitor 2
             wtemp=ChangeBinOffset(__MonWS,t1f*16667,sp1,sp1)
             wtemp=ChangeBinOffset(wtemp,t2f*16667,sp2,sp2)
             wtemp=Rebin(InputWorkspace=wtemp,Params="1",PreserveEvents=True)
             
             #check whether the fermi chopper is in the beam
             fermi=__MonWS.run().getProperty('vChTrans').value[0]

             if fermi == 2 :
                 Efixed = nan
                 T0 = nan
                 DeleteWorkspace(wtemp)

             if fermi != 2:
                 alg=GetEi(InputWorkspace=wtemp,Monitor1Spec=sp1+1,Monitor2Spec=sp2+1,EnergyEstimate=Eguess)   #Run GetEi algorithm
                 Efixed=alg[0]
                 T0=alg[3]                                        #Extract incident energy and T0
                 DeleteWorkspace(wtemp)
    except e:    
            [Efixed,T0]=GetEiT0atSNS("__MonWS",Eguess)

    #if Efixed!='N/A':
    LoadEventNexus(Filename=filename,OutputWorkspace="__IWS",Precount=0) #Load an event Nexus file
    #Fix that all time series log values start at the same time as the proton_charge
    CorrectLogTimes('__IWS')
    #FilterByLogValue("__IWS",OutputWorkspace="__IWS",LogName="CCR22Rot",MinimumValue=52.2,MaximumValue=52.4)
    #Filter chopper 3 bad events
    valC3=__MonWS.getRun()['Phase3'].getStatistics().median
    #FilterByLogValue(InputWorkspace='__IWS',OutputWorkspace='__IWS',LogName='Phase3',MinimumValue=valC3-0.15,MaximumValue=valC3+0.15)
    #FilterBadPulses(InputWorkspace="__IWS",OutputWorkspace = "__IWS",LowerCutoff = 50)
    return [Eguess,Efixed,T0]
  
    
def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
          
if __name__ == "__main__":
    numpy.seterr("ignore")#ignore division by 0 warning in plots
    #processing parameters
    RawVanadium="/SNS/SEQ/2014_1_17_CAL/nexus/SEQ_47123.nxs.h5"
    ProcessedVanadium='van47123.nxs'
    HardMaskFile=''
    IntegrationRange=[0.3,1.2] #integration range for Vanadium in angstroms
    MaskBTPParameters=[{'Pixel':"1-8,121-128"}]
    MaskBTPParameters.append({'Bank':"99-102,114,115,141,75,76,38,39,62,65"})
    
    MaskBTPParameters.append({'Bank':"122",'Tube':"3"})
    MaskBTPParameters.append({'Bank':"127",'Tube':"4"})
    MaskBTPParameters.append({'Bank':"142",'Tube':"1"})
    MaskBTPParameters.append({'Bank':"144",'Tube':"1"})
    MaskBTPParameters.append({'Bank':"147",'Tube':"7"})
    MaskBTPParameters.append({'Bank':"147",'Tube':"4"})
    
    MaskBTPParameters.append({'Bank':"83",'Tube':"1"})
    MaskBTPParameters.append({'Bank':"96",'Tube':"2"})
    MaskBTPParameters.append({'Bank':"97",'Tube':"4"})
    MaskBTPParameters.append({'Bank':"112",'Tube':"7"})
    MaskBTPParameters.append({'Bank':"113",'Tube':"7"})



    MaskBTPParameters.append({'Bank':"51",'Tube':"6"})
    MaskBTPParameters.append({'Bank':"55",'Tube':"8"})
    MaskBTPParameters.append({'Bank':"63",'Tube':"3"})
    MaskBTPParameters.append({'Bank':"63",'Tube':"8"})
    MaskBTPParameters.append({'Bank':"71",'Tube':"8"})
    MaskBTPParameters.append({'Bank':"74",'Tube':"2"})
    
    
    #Added these masked pixels for HOT spots on detector
    MaskBTPParameters.append({'Bank':"127", 'Tube':'7,8', 'Pixel':'101-114'})
    MaskBTPParameters.append({'Bank':"88",'Tube':"3-4",'Pixel':"32-36"})
    #MaskBTPParameters.append({'Bank':"105",'Tube':"5",'Pixel':"89-91"})
    MaskBTPParameters.append({'Bank':"46",'Tube':"7-8",'Pixel':"102-111"})
    
    
    clean=True
    NXSPE_flag=True

    NormalizedVanadiumEqualToOne = True

    #check number of arguments
    if (len(sys.argv) != 3): 
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
        filename = sys.argv[1]
        outdir = sys.argv[2]
        if filename.endswith('.nxs'):
            outdir+='LEGACY/'

    elog=ExperimentLog()
    elog.setLogList('vChTrans,Speed1,Phase1,Speed2,Phase2,Speed3,Phase3,EnergyRequest,s1t,s1r,s1l,s1b,vAttenuator2,vAttenuator1,svpressure,dvpressure')
    elog.setSimpleLogList("vChTrans, EnergyRequest, s1t, s1r, s1l, s1b, vAttenuator2, vAttenuator1")
    elog.setSERotOptions('CCR13VRot, SEOCRot, CCR16Rot, CCR22Rot')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorA')
    elog.setFilename(outdir+'experiment_log.csv')

    DGSdict=preprocessVanadium(RawVanadium,outdir+ProcessedVanadium,MaskBTPParameters)
    [EGuess,Ei,T0]=preprocessData(filename)
    angle=elog.save_line('__MonWS',CalculatedEi=Ei,CalculatedT0=T0)    
    outpre='SEQ'
    runnum=str(mtd['__IWS'].getRunNumber()) 
    outfile=outpre+'_'+runnum+'_autoreduced'
    if not math.isnan(Ei):
        DGSdict['SampleInputWorkspace']='__IWS'
        DGSdict['SampleInputMonitorWorkspace']='__MonWS'
        DGSdict['IncidentEnergyGuess']=Ei
        DGSdict['UseIncidentEnergyGuess']='1'
        DGSdict['TimeZeroGuess']=T0
        DGSdict['EnergyTransferRange']=[-0.25*EGuess,0.005*EGuess,0.95*EGuess]  #Typical values are -0.5*EGuess, 0.005*EGuess, 0.95*EGuess
        DGSdict['SofPhiEIsDistribution']='0' # keep events
        DGSdict['HardMaskFile']=HardMaskFile
        DGSdict['GroupingFile']='/SNS/SEQ/shared/autoreduce/SEQ_2x2_grouping.xml' #Typically an empty string '', choose 2x1 or some other grouping file created by GenerateGroupingSNSInelastic or GenerateGroupingPowder
        DGSdict['IncidentBeamNormalisation']='None'  #NEXUS file does not have any normaliztion, but the nxspe IS normalized later in code by charge
        DGSdict['UseBoundsForDetVan']='1'
        DGSdict['DetVanIntRangeHigh']=IntegrationRange[1]
        DGSdict['DetVanIntRangeLow']=IntegrationRange[0]
        DGSdict['DetVanIntRangeUnits']='Wavelength'
        DGSdict['OutputWorkspace']='__OWS'
        DgsReduction(**DGSdict)
        

        #Do normalization of vanadum to 1
        # This step only runs ONCE if the processed vanadium file is not already present.
        if DGSdict.has_key('SaveProcessedDetVan') and NormalizedVanadiumEqualToOne:
              filename=DGSdict['SaveProcDetVanFilename']
              LoadNexus(Filename=filename,OutputWorkspace="__VAN")
              datay = mtd['__VAN'].extractY()
              meanval = float(datay[datay>0].mean())
              CreateSingleValuedWorkspace(OutputWorkspace='__meanval',DataValue=meanval)
              Divide(LHSWorkspace='__VAN',RHSWorkspace='__meanval',OutputWorkspace='__VAN') #Divide the vanadium by the mean
              Multiply(LHSWorkspace='__OWS',RHSWorkspace='__meanval',OutputWorkspace='__OWS') #multiple by the mean of vanadium Normalized data = Data / (Van/meanvan) = Data *meanvan/Van
              SaveNexus(InputWorkspace="__VAN", Filename= filename)        
        
        
        AddSampleLog(Workspace="__OWS",LogName="psi",LogText=str(angle),LogType="Number")
        SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
        RebinToWorkspace(WorkspaceToRebin="__OWS",WorkspaceToMatch="__OWS",OutputWorkspace="__OWS",PreserveEvents='0')
        NormaliseByCurrent(InputWorkspace="__OWS",OutputWorkspace="__OWS")
        ConvertToDistribution(Workspace="__OWS") 		                                                                #Divide by bin width
        
        s=SumSpectra("__OWS")
        x=s.readX(0)
        y=s.readY(0)
        plot(x[1:],y)
        xlabel('Energy transfer (meV)')
        ylabel('Intensity')
        yscale('log')
        show()
        savefig(outdir+outfile+'nxs.png',bbox_inches='tight')
        
        if NXSPE_flag:            
            SaveNXSPE(InputWorkspace="__OWS", Filename= outdir+outfile+".nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True) 
        if clean:
            WS_clean()
    else:
       ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
       Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.5,0.005,10',PreserveEvents='0')
       SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
                                                    

