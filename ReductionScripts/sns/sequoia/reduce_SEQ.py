#!/usr/bin/env python
import sys,os,math
sys.path.append("/opt/Mantid/bin")
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
        # adjust time for pack B15 wired strangely
        ChangeBinOffset(InputWorkspace="__VAN",OutputWorkspace="__VAN",Offset=500,IndexMin=14336,IndexMax=15359) 
        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        dictvan={'SaveProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN','SaveProcDetVanFilename':Processed}
    return dictvan
        
def preprocessData(filename):
    f1 = os.path.split(filename)[-1]
    runnum = int(f1.strip('SEQ_').replace('.nxs.h5',''))
    __MonWS=LoadNexusMonitors(Filename=filename)

    #Example of PV streamer not running. Copying logs from some other run
    #if (runnum >= 55959 and runnum <= 55960):
    #    LoadNexusLogs(__MonWS,"/SNS/SEQ/IPTS-10531/nexus/SEQ_55954.nxs.h5")
    #
    
    #Example of filtering by a logvalue
    #FilterByLogValue("__MonWS",OutputWorkspace="__MonWS",LogName="CCR22Rot",MinimumValue=52.2,MaximumValue=52.4)

    Eguess=__MonWS.getRun()['EnergyRequest'].getStatistics().mean
    #check whether the fermi chopper is in the beam
    fermi=__MonWS.run().getProperty('vChTrans').value[0]

    if fermi == 2 :
        Efixed = numpy.nan
        T0 = numpy.nan
        
    else:
        [Efixed,T0]=GetEiT0atSNS("__MonWS",Eguess)

    #Load an event Nexus file
    LoadEventNexus(Filename=filename,OutputWorkspace="__IWS",Precount=0) 

    #Fix that all time series log values start at the same time as the proton_charge
    CorrectLogTimes('__IWS')
    
    # adjust time for pack B15 wired strangely
    ChangeBinOffset(InputWorkspace="__IWS",OutputWorkspace="__IWS",Offset=500,IndexMin=14336,IndexMax=15359)

    #delete all bad pulses below   10% of the average of the file.
    FilterBadPulses(InputWorkspace="__IWS",OutputWorkspace = "__IWS",LowerCutoff = 10)
    return [Eguess,Efixed,T0]
  
    
def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
          
if __name__ == "__main__":
    numpy.seterr("ignore")#ignore division by 0 warning in plots
    #processing parameters
    RawVanadium="/SNS/SEQ/IPTS-14730/nexus/SEQ_80013.nxs.h5"
    ProcessedVanadium="van80013b.nxs"
    HardMaskFile=''
    IntegrationRange=[0.3,1.2] #integration range for Vanadium in angstroms
    MaskBTPParameters=[{'Pixel':"1-8,121-128"}]
    #short packs around beam stop, and uninstalled packs at far left
    #MaskBTPParameters.append({'Bank':"99-102,114,115,75,76,38,39"})
 
    #MaskBTPParameters.append({'Bank':"62,92"})
    #MaskBTPParameters.append({'Bank':"98",'Tube':"6-8"})
    #MaskBTPParameters.append({'Bank':"108",'Tube':"4"})
    #MaskBTPParameters.append({'Bank':"141"})
    #MaskBTPParameters.append({'Bank':"70"})
    MaskBTPParameters.append({'Pixel': '1-8,121-128'})
    MaskBTPParameters.append({'Bank': '114,115,75,76,38,39'})
    MaskBTPParameters.append({'Tube': '1', 'Bank': '116'})


 # only for the runs in IPTS-11831
 #   MaskBTPParameters.append({'Bank':"61-74,98-113,137-150"})
    
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
    elog.setSERotOptions('CCR13VRot, SEOCRot, CCR16Rot, CCR22Rot, phi')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorA, SensorA340 ')
    elog.setFilename(outdir+'experiment_log.csv')

    processed_van_file = ProcessedVanadium
    if not os.path.isabs(processed_van_file):
        processed_van_file = os.path.join(outdir, ProcessedVanadium)

    DGSdict=preprocessVanadium(RawVanadium, processed_van_file, MaskBTPParameters)
    #--------------------------------------
    #Preprocess data to get Ei and T0
    #--------------------------------------
    [EGuess,Ei,T0]=preprocessData(filename)
    angle=elog.save_line('__MonWS',CalculatedEi=Ei,CalculatedT0=T0)    #If angles not saved to file, put them by hand here and re-run reduction one by one.
    #angle= 99.99 #This is where you can manually set the rotation angle
    outpre='SEQ'
    runnum=str(mtd['__IWS'].getRunNumber()) 
    outfile=outpre+'_'+runnum+'_autoreduced'
    if not math.isnan(Ei):
        DGSdict['SampleInputWorkspace']='__IWS'
        DGSdict['SampleInputMonitorWorkspace']='__MonWS'
        DGSdict['IncidentEnergyGuess']=Ei
        DGSdict['UseIncidentEnergyGuess']='1'
        DGSdict['TimeZeroGuess']=T0
        DGSdict['EnergyTransferRange']=[-0.5*EGuess,0.005*EGuess,0.95*EGuess]  #Typical values are -0.5*EGuess, 0.005*EGuess, 0.95*EGuess
        DGSdict['SofPhiEIsDistribution']='0' # keep events
        DGSdict['HardMaskFile']=HardMaskFile
        DGSdict['GroupingFile']="/SNS/SEQ/shared/autoreduce/SEQ_2x2_grouping.xml"#'/SNS/SEQ/shared/autoreduce/SEQ_2x2_grouping.xml' #Typically an empty string '', choose 2x1 or some other grouping file created by GenerateGroupingSNSInelastic or GenerateGroupingPowder
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
#generate summed spectra_plot
#---------------------------------------          
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
            GenerateGroupingPowder(InputWorkspace="__OWS",AngleStep=0.5, GroupingFilename=outdir+'powdergroupfile.xml')
            GroupDetectors(InputWorkspace="__OWS", OutputWorkspace="powdergroupdata", MapFile=outdir+'powdergroupfile.xml',Behaviour='Average')
            SaveNXSPE(InputWorkspace="powdergroupdata", Filename= outdir+"/powder/"+outfile+"_powder.nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True,ParFile=outdir+'powdergroupfile.par') 
        if clean:
            WS_clean()
    else:
       ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
       Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.5,0.005,10',PreserveEvents='0')
       SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
                                                    

