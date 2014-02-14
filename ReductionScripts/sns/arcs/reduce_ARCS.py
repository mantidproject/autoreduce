#!/usr/bin/env python
import sys,os,math
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")

sys.path.append("/opt/mantidnightly/bin")
from ARLibrary import * #note that ARLibrary would set mantidpath as well
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *

# Logs at: /var/log/SNS_applications/autoreduce.log

def preprocessVanadium(Raw,Processed,Parameters):
    if os.path.isfile(Processed):
        LoadNexus(Filename=Processed,OutputWorkspace="__VAN")
        dictvan={'UseProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN'}
    else:
        LoadEventNexus(Filename=Raw,OutputWorkspace="__VAN")
        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        dictvan={'SaveProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN','SaveProcDetVanFilename':Processed}
    return dictvan
        
def preprocessData(filename):
    __MonWS=LoadNexusMonitors(Filename=filename)
    Eguess=__MonWS.getRun()['EnergyRequest'].getStatistics().mean
    [Efixed,T0]=GetEiT0atSNS("__MonWS",Eguess)


    #if Efixed!='N/A':
    LoadEventNexus(Filename=filename,OutputWorkspace="__IWS") #Load an event Nexus file
    #Fix that all time series log values start at the same time as the proton_charge
    CorrectLogTimes('__IWS')

    #Add other Filters here
    #Filter chopper 3 bad events
    #valC3=__MonWS.getRun()['Phase3'].getStatistics().median
    #FilterByLogValue(InputWorkspace='__IWS',OutputWorkspace='__IWS',LogName='Phase3',MinimumValue=valC3-0.15,MaximumValue=valC3+0.15)
    #FilterBadPulses(InputWorkspace="__IWS",OutputWorkspace = "__IWS",LowerCutoff = 50)
    return [Eguess,Efixed,T0]

def CheckPacks(inputWorkspace,outdir) :
    #check here for bad packs - added 2014-2-14 by JLN
    packgroupfile = '/SNS/ARCS/shared/groupingfiles/ARCS_Grouped_Banks.xml'
    GroupDetectors(inputWorkspace,OutputWorkspace='__IWSBanks',MapFile="/SNS/ARCS/shared/groupingfiles/ARCS_Grouped_Banks.xml")
    runnum=str(inputWorkspace.getRunNumber())   
    zero_packs=[]
    for j in range(mtd['__IWSBanks'].getNumberHistograms()) :		
        #get the value of summed counts from the pack
        packvals = mtd['__IWSBanks'].extractY()[j]		
        if packvals[0] == 0:
            zero_packs.append(str(j))
    DeleteWorkspace('__IWSBanks')

    #output to the file only if there are zero packs
    if len(zero_packs) > 0:
        pack_file=open(outdir+'pack_report','a')
        pack_string = str.join(' ',zero_packs)
        pack_file.write("run {1} zero counts in packs: {0}\n".format(pack_string,runnum))
        pack_file.close()
 
  

def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
    
          
if __name__ == "__main__":

    #processing parameters
    RawVanadium="/SNS/ARCS/2014_1_18_CAL/data/ARCS_44789_event.nxs"
    ProcessedVanadium='van44789.nxs'
    HardMaskFile=''
    IntegrationRange=[0.35,0.75] #integration range for Vanadium in angstroms
    MaskBTPParameters=[{'Pixel':"1-7,122-128"}]
    MaskBTPParameters.append({'Bank':"70",'Pixel':"1-12,117-128"})
    MaskBTPParameters.append({'Bank':"71",'Pixel':"1-14,115-128"})
    groupingFile=''  #this is the grouping file, powder.xml, 2X1.xml and so on. needs the full path for this file.
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


    elog=ExperimentLog()
    elog.setLogList('vChTrans,Speed1,Phase1,Speed2,Phase2,Speed3,Phase3,EnergyRequest,s1t,s1r,s1l,s1b,s2t,s2r,s2l,s2b')
    elog.setSimpleLogList("vChTrans, EnergyRequest, s1t, s1r, s1l, s1b,s2t,s2r,s2l,s2b")
    elog.setSERotOptions('CCR12Rot, SEOCRot, CCR16Rot, SEHOT11, micas70mmRot')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorA, SensorB, SensorC, SensorD')
    elog.setFilename(outdir+'experiment_log.csv')

   

    DGSdict=preprocessVanadium(RawVanadium,outdir+ProcessedVanadium,MaskBTPParameters)
    [EGuess,Ei,T0]=preprocessData(filename)

    CheckPacks(mtd['__IWS'],outdir)
    angle=elog.save_line('__MonWS',CalculatedEi=Ei,CalculatedT0=T0)  
    outpre='ARCS'
    runnum=str(mtd['__IWS'].getRunNumber()) 
    outfile=outpre+'_'+runnum+'_autoreduced'  
    if not math.isnan(Ei):
        DGSdict['SampleInputWorkspace']='__IWS'
        DGSdict['SampleInputMonitorWorkspace']='__MonWS'
        DGSdict['IncidentEnergyGuess']=Ei
        DGSdict['UseIncidentEnergyGuess']='1'
        DGSdict['TimeZeroGuess']=T0
        DGSdict['EnergyTransferRange']=[-0.5*EGuess,0.01*EGuess,0.9*EGuess] #Energy Binning
        DGSdict['SofPhiEIsDistribution']='0' # keep events (need to then run RebinToWorkspace and ConvertToDistribution)
        DGSdict['HardMaskFile']=HardMaskFile
        DGSdict['GroupingFile']=groupingFile #choose 2x1 or some other grouping file created by GenerateGroupingSNSInelastic or GenerateGroupingPowder
        DGSdict['IncidentBeamNormalisation']='ByCurrent'
        DGSdict['UseBoundsForDetVan']='1'
        DGSdict['DetVanIntRangeHigh']=IntegrationRange[1]
        DGSdict['DetVanIntRangeLow']=IntegrationRange[0]
        DGSdict['DetVanIntRangeUnits']='Wavelength'
        DGSdict['MedianTestLevelsUp']='1'
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
              Divide(LHSWorkspace='__VAN',RHSWorkspace='__meanval',OutputWorkspace='__VAN')  #Divide the vanadium by the mean
              Multiply(LHSWorkspace='__OWS',RHSWorkspace='__meanval',OutputWorkspace='__OWS') #multiple by the mean of vanadium Normalized data = Data / (Van/meanvan) = Data *meanvan/Van
              SaveNexus(InputWorkspace="__VAN", Filename= filename)
        AddSampleLog(Workspace="__OWS",LogName="psi",LogText=str(angle),LogType="Number")  
        SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")
        RebinToWorkspace(WorkspaceToRebin="__OWS",WorkspaceToMatch="__OWS",OutputWorkspace="__OWS",PreserveEvents='0')
        ConvertToDistribution(Workspace="__OWS") 		                                                                #Divide by bin width

        if NXSPE_flag:            
            SaveNXSPE(InputWorkspace="__OWS", Filename= outdir+outfile+".nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True) 
                    
        #plots
        minvals,maxvals=ConvertToMDHelper('__OWS','|Q|','Direct')
        xmin=minvals[0]
        xmax=maxvals[0]
        xstep=(xmax-xmin)*0.01
        ymin=minvals[1]
        ymax=maxvals[1]
        ystep=(ymax-ymin)*0.01
        x=arange(xmin,xmax,xstep)[0:100]
        y=arange(ymin,ymax,ystep)[0:100]
        X,Y=meshgrid(x,y)


        MD=ConvertToMD('__OWS',QDimensions='|Q|',dEAnalysisMode='Direct',MinValues=minvals,MaxValues=maxvals)
        ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
        ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
        MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
        d=MDH.getSignalArray()
        ne=MDH.getNumEventsArray()
        dne=d/ne

        Zm=ma.masked_where(ne==0,dne)
        pcolormesh(X,Y,log(Zm),shading='gouraud')
        xlabel('|Q| ($\AA^{-1}$)')
        ylabel('E (meV)')
        title("Run "+outfile)

        savefig(str(outdir+outfile+".nxs.png"),bbox_inches='tight')


        if clean:
            WS_clean()
   
    else:  #Do this if it is whitebeam
       ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
       Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.1,0.005,5',PreserveEvents='0')
       SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")                                                 

