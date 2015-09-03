#!/usr/bin/env python
import sys,os
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
# Logs at: /var/log/SNS_applications/autoreduce.log
import numpy
from ARLibrary import * #note that ARLibrary would set mantidpath as well

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
    AddSampleLogMultiple("__IWS","CalculatedEi,CalculatedT0",str(Efixed)+','+str(T0))
    return [Eguess,Efixed,T0]
  
    
def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
          
if __name__ == "__main__":
    numpy.seterr("ignore")#ignore division by 0 warning in plots
    #processing parameters
    RawVanadium="/SNS/SEQ/IPTS-14730/nexus/SEQ_80033.nxs.h5"
    ProcessedVanadium="van80033C.nxs"
    HardMaskFile=''
    IntegrationRange=[0.3,1.2] #integration range for Vanadium in angstroms
    MaskBTPParameters=[]
    MaskBTPParameters.append({'Pixel': '1-8,121-128'})
    MaskBTPParameters.append({'Bank': '114,115,75,76,38,39'})
    MaskBTPParameters.append({'Tube': '1', 'Bank': '116'})
    MaskBTPParameters.append({'Tube': '7', 'Pixel': '104-107', 'Bank': '46'})
    MaskBTPParameters.append({'Tube': '2', 'Pixel': '53-55', 'Bank': '81'})
    MaskBTPParameters.append({'Tube': '3', 'Pixel': '33-35', 'Bank': '88'})
    MaskBTPParameters.append({'Tube': '8', 'Pixel': '104-111', 'Bank': '127'})
    MaskBTPParameters.append({'Tube': '7', 'Pixel': '23-25', 'Bank': '139'})
    MaskBTPParameters.append({'Tube': '5', 'Bank': '45'})
    MaskBTPParameters.append({'Tube': '8', 'Bank': '70'})
    MaskBTPParameters.append({'Tube': '4', 'Bank': '148'})
    MaskBTPParameters.append({'Bank': '52'})
    MaskBTPParameters.append({'Bank': '99-102'})
    MaskBTPParameters.append({'Bank': '59'})
 
    #uninstalled packs at far left
    #MaskBTPParameters.append({'Bank':"114,115,75,76,38,39"})
 
    #examples of how to mask, but these should be done with the web interface.
    #MaskBTPParameters.append({'Bank':"62,92"})
    #MaskBTPParameters.append({'Bank':"98",'Tube':"6-8"})
    #MaskBTPParameters.append({'Bank':"108",'Tube':"4"})
    #MaskBTPParameters.append({'Bank':"141"})
    #MaskBTPParameters.append({'Bank':"70"})

    #MaskBTPParameters.append({'Pixel': '1-8,121-128'})
    #MaskBTPParameters.append({'Bank': '114,115,75,76,38,39'})
    #MaskBTPParameters.append({'Tube': '1', 'Bank': '116'})

    
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


    processed_van_file = ProcessedVanadium
    if not os.path.isabs(processed_van_file):
        processed_van_file = os.path.join(outdir, ProcessedVanadium)

    DGSdict=preprocessVanadium(RawVanadium, processed_van_file, MaskBTPParameters)
    #--------------------------------------
    #Preprocess data to get Ei and T0
    #--------------------------------------
    [EGuess,Ei,T0]=preprocessData(filename)
    """

    if os.path.isfile(outdir+'experiment_log.csv'):
        fm='fastappend'
    else:
        fm='new'
        
    snames='RunNumber,Title,Comment,StartTime,EndTime,Duration,ProtonCharge,'+\
    'vChTrans,Speed1,Speed1,Speed1,Phase1,Phase1,Phase1,Speed2,Speed2,Speed2,'+\
    'Phase2,Phase2,Phase2,Speed3,Speed3,Speed3,Phase3,Phase3,Phase3,EnergyRequest,s1t,s1r,s1l,s1b,'+\
    'vAttenuator2,vAttenuator1,svpressure,svpressure,svpressure,dvpressure,dvpressure,dvpressure'+\
    'phi,phi,phi,Lakeshore1SensorA,Lakeshore1SensorA,Lakeshore1SensorA,'+\
    'Lakeshore1SensorB,Lakeshore1SensorB,Lakeshore1SensorB,'+\
    'Lakeshore1SensorC,Lakeshore1SensorC,Lakeshore1SensorC,'+\
    'Lakeshore1SensorD,Lakeshore1SensorD,Lakeshore1SensorD,'+\
    'Lakeshore2SensorA,Lakeshore2SensorA,Lakeshore2SensorA,'+\
    'Lakeshore2SensorB,Lakeshore2SensorB,Lakeshore2SensorB,'+\
    'Lakeshore2SensorC,Lakeshore2SensorC,Lakeshore2SensorC,'+\
    'Lakeshore2SensorD,Lakeshore2SensorD,Lakeshore2SensorD,'+\
    'SampleTemperatureOrangeCryo,SampleTemperatureOrangeCryo,SampleTemperatureOrangeCryo,CalculatedEi,CalculatedT0'
    
    stitles='RunNumber,Title,Comment,StartTime,EndTime,Duration,ProtonCharge,'+\
    'vChTrans,Speed1min,Speed1max,Speed1avg,Phase1min,Phase1max,Phase1avg,Speed2min,Speed2max,Speed2avg,'+\
    'Phase2min,Phase2max,Phase2avg,Speed3min,Speed3max,Speed3avg,Phase3min,Phase3max,Phase3avg,'+\
    'EnergyRequest,s1t,s1r,s1l,s1b,'+\
    'vAttenuator2,vAttenuator1,svpressuremin,svpressuremax,svpressureavg,dvpressuremin,dvpressuremax,dvpressureavg'+\
    'phimin,phimax,phiavg,Lakeshore1SensorAmin,Lakeshore1SensorAmax,Lakeshore1SensorAavg,'+\
    'Lakeshore1SensorBmin,Lakeshore1SensorBmax,Lakeshore1SensorBavg,'+\
    'Lakeshore1SensorCmin,Lakeshore1SensorCmax,Lakeshore1SensorCavg,'+\
    'Lakeshore1SensorDmin,Lakeshore1SensorDmax,Lakeshore1SensorDavg,'+\
    'Lakeshore2SensorAmin,Lakeshore2SensorAmax,Lakeshore2SensorAavg,'+\
    'Lakeshore2SensorBmin,Lakeshore2SensorBmax,Lakeshore2SensorBavg,'+\
    'Lakeshore2SensorCmin,Lakeshore2SensorCmax,Lakeshore2SensorCavg,'+\
    'Lakeshore2SensorDmin,Lakeshore2SensorDmax,Lakeshore2SensorDavg,'+\
    'SampleTemperatureOrangeCryomin,SampleTemperatureOrangeCryomax,SampleTemperatureOrangeCryoavg,CalculatedEi,CalculatedT0'
    
    
    soperations = ['0']*len(snames.split(','))
    
    for i,name in enumerate(stitles.split(',')):
        name=name.strip()
        if name in ['RunNumber','Title','Comment','StartTime','EndTime']:
            soperations[i] = 'None'
        if name.find('min') == len(name)-3:
            soperations[i] = 'min'
        if name.find('max') == len(name)-3:
            soperations[i] = 'max'
        if name.find('avg') == len(name)-3:
            soperations[i] = 'average'
                           
    
    ExportExperimentLog(InputWorkspace = '__IWS',
                        OutputFilename = outdir+'experiment_log.csv',
                        FileMode = fm,
                        SampleLogNames = snames,
                        SampleLogTitles = stitles,
                        SampleLogOperation = ','.join(soperations),
                        FileFormat = "comma (csv)",
                        TimeZone = "America/New_York")
    """
    elog=ExperimentLog()
    elog.setLogList('vChTrans,Speed1,Phase1,Speed2,Phase2,Speed3,Phase3,EnergyRequest,s1t,s1r,s1l,s1b,s2t, s2r, s2l, s2b,  vAttenuator2,vAttenuator1,svpressure,dvpressure,Lakeshore1SensorA, Lakeshore1SensorB, Lakeshore2SensorB')
    elog.setSimpleLogList("vChTrans, EnergyRequest, s1t, s1r, s1l, s1b, s2t, s2r, s2l, s2b, vAttenuator2, vAttenuator1, Lakeshore1SensorA, Lakeshore1SensorB, Lakeshore2SensorB")
    elog.setSERotOptions('CCR13VRot, SEOCRot, CCR16Rot, CCR22Rot,phi')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorA, SensorA340 ')
    elog.setFilename(outdir+'experiment_log.csv')
    angle=elog.save_line('__MonWS',CalculatedEi=Ei,CalculatedT0=T0)
    
    outpre='SEQ'
    runnum=str(mtd['__IWS'].getRunNumber()) 
    outfile=outpre+'_'+runnum+'_autoreduced'
    if not numpy.isnan(Ei):
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
              #Divide the vanadium by the mean
              Divide(LHSWorkspace='__VAN',RHSWorkspace='__meanval',OutputWorkspace='__VAN') 
              #multiple by the mean of vanadium Normalized data = Data / (Van/meanvan) = Data *meanvan/Van
              Multiply(LHSWorkspace='__OWS',RHSWorkspace='__meanval',OutputWorkspace='__OWS') 
              SaveNexus(InputWorkspace="__VAN", Filename= filename)        
        
        SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
        RebinToWorkspace(WorkspaceToRebin="__OWS",WorkspaceToMatch="__OWS",OutputWorkspace="__OWS",PreserveEvents='0')
        NormaliseByCurrent(InputWorkspace="__OWS",OutputWorkspace="__OWS")
        #Divide by bin width
        ConvertToDistribution(Workspace="__OWS") 
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
            angle=mtd["__OWS"].run()['phi'].getStatistics().mean      
            SaveNXSPE(InputWorkspace="__OWS", Filename= outdir+outfile+".nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True)
            GenerateGroupingPowder(InputWorkspace="__OWS",AngleStep=0.5, GroupingFilename=outdir+'powdergroupfile.xml')
            GroupDetectors(InputWorkspace="__OWS", OutputWorkspace="powdergroupdata", MapFile=outdir+'powdergroupfile.xml',Behaviour='Average')
            SaveNXSPE(InputWorkspace="powdergroupdata", Filename= outdir+"/powder/"+outfile+"_powder.nxspe",
                      Efixed=Ei,Psi=angle,KiOverKfScaling=True,ParFile=outdir+'powdergroupfile.par') 
        if clean:
            WS_clean()
    else:
       ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
       Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.5,0.005,10',PreserveEvents='0')
       SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
                                                    

