#!/usr/bin/env python
import sys,os
sys.path.append("/opt/Mantid/bin")
from ARLibrary import * #note that ARLibrary would set mantidpath as well
from mantid.simpleapi import *

# Logs at: /var/log/SNS_applications/autoreduce.log

def preprocessVanadium(Raw,Processed,Parameters):
    if os.path.isfile(Processed):
        LoadNexus(Filename=Processed,OutputWorkspace="__VAN")
        dictvan={'UseProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN'}
    else:
        LoadEventNexus(Filename=Raw,OutputWorkspace="__VAN")
        #ChangeBinOffset(InputWorkspace="__VAN",OutputWorkspace="__VAN",Offset=500,IndexMin=54272,IndexMax=55295) # adjust time for pack C17 wired backward
        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        dictvan={'SaveProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN','SaveProcDetVanFilename':Processed}
    return dictvan
        
def preprocessData(filename):
    __MonWS=LoadNexusMonitors(Filename=filename)
    Eguess=__MonWS.getRun()['EnergyRequest'].getStatistics().mean
    ###########################
    #Temporary workaround for IPTS-9145  GEG
    if Eguess<5:
      Eguess=50.
    ###################  
    [Efixed,T0]=GetEiT0("__MonWS",Eguess)

    #if Efixed!='N/A':
    LoadEventNexus(Filename=filename,OutputWorkspace="__IWS") #Load an event Nexus file
    #Fix that all time series log values start at the same time as the proton_charge
    CorrectLogs('__IWS')

    #Filter chopper 3 bad events
    valC3=__MonWS.getRun()['Phase3'].getStatistics().median
    FilterByLogValue(InputWorkspace='__IWS',OutputWorkspace='__IWS',LogName='Phase3',MinimumValue=valC3-0.15,MaximumValue=valC3+0.15)
    #FilterBadPulses(InputWorkspace="__IWS",OutputWorkspace = "__IWS",LowerCutoff = 50)
    return [Eguess,Efixed,T0]
  
    
def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
          
if __name__ == "__main__":

    #processing parameters
    RawVanadium="/SNS/SEQ/shared/2013_B/V_files/SEQ_42458.nxs.h5"
    ProcessedVanadium='van.nxs'
    HardMaskFile=''
    IntegrationRange=[0.3,1.2] #integration range for Vanadium in angstroms
    MaskBTPParameters=[{'Pixel':"1,2,3,4,5,6,7,8,121,122,123,124,125,126,127,128"}]
    MaskBTPParameters.append({'Bank':"99,100,101,102"})
    clean=True
    NXSPE_flag=True

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
    if Ei!='N/A':
        DGSdict['SampleInputWorkspace']='__IWS'
        DGSdict['SampleInputMonitorWorkspace']='__MonWS'
        DGSdict['IncidentEnergyGuess']=Ei
        DGSdict['UseIncidentEnergyGuess']='1'
        DGSdict['TimeZeroGuess']=T0
        DGSdict['EnergyTransferRange']=[-0.5*EGuess,0.005*EGuess,0.95*EGuess]
        DGSdict['SofPhiEIsDistribution']='0' # keep events
        DGSdict['HardMaskFile']=HardMaskFile
        DGSdict['GroupingFile']='' #choose 2x1 or some other grouping file created by GenerateGroupingSNSInelastic or GenerateGroupingPowder
        DGSdict['IncidentBeamNormalisation']='None'
        DGSdict['UseBoundsForDetVan']='1'
        DGSdict['DetVanIntRangeHigh']=IntegrationRange[1]
        DGSdict['DetVanIntRangeLow']=IntegrationRange[0]
        DGSdict['DetVanIntRangeUnits']='Wavelength'
        DGSdict['OutputWorkspace']='__OWS'
        DgsReduction(**DGSdict)
        AddSampleLog(Workspace="__OWS",LogName="psi",LogText=str(angle),LogType="Number")
        SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
        RebinToWorkspace(WorkspaceToRebin="__OWS",WorkspaceToMatch="__OWS",OutputWorkspace="__OWS",PreserveEvents='0')
        NormaliseByCurrent(InputWorkspace="__OWS",OutputWorkspace="__OWS")
        ConvertToDistribution(Workspace="__OWS") 		                                                                #Divide by bin width

        if NXSPE_flag:            
            SaveNXSPE(InputWorkspace="__OWS", Filename= outdir+outfile+".nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True) 
        if clean:
            WS_clean()
    else:
       ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
       Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.5,0.005,10',PreserveEvents='0')
       SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
                                                    

