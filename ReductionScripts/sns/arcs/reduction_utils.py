#!/usr/bin/env python
import sys,os,math
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")

sys.path.append("/opt/Mantid/bin")
import numpy
numpy.seterr(all='ignore') # added Dec 8, 2016 to suppress divide by zero warning following what is done in HYSPEC autoreduce script
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

        #added to fix 500 microsecond offset on pack 35 for run 2014-B - not needed now
        #ChangeBinOffset(InputWorkspace="__VAN",OutputWorkspace="__VAN", Offset=500, IndexMin=34816, IndexMax=35839)

        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        zeroDets=FindDetectorsOutsideLimits("__VAN")
        MaskDetectors(Workspace="__VAN",MaskedWorkspace=zeroDets[0])
        dictvan={'SaveProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN','SaveProcDetVanFilename':Processed}
    return dictvan


def computeT0(Ei):
    return 125.0*numpy.power(Ei, -0.5255)

def preprocessData(filename):
    __MonWS=LoadNexusMonitors(Filename=filename)
    Eguess=__MonWS.getRun()['EnergyRequest'].getStatistics().mean

    #if Efixed!='N/A':
    LoadEventNexus(Filename=filename,OutputWorkspace="__IWS") #Load an event Nexus file
    #added to fix 500 microsecond offset on pack 35 for run 2014-B - not needed now
    #ChangeBinOffset(InputWorkspace="__IWS",OutputWorkspace="__IWS", Offset=500, IndexMin=34816, IndexMax=35839)
    #Fix that all time series log values start at the same time as the proton_charge
    CorrectLogTimes('__IWS')

    # uncomment the following if using two monitors
    getEi_from_monitors_failed = False
    try:
        Efixed, _mp, _mi, T0 = GetEiMonDet(Version=1, DetectorWorkspace="__IWS",MonitorWorkspace=__MonWS,EnergyGuess=Eguess,MonitorSpectrumNumber=1)
    except:
        getEi_from_monitors_failed = True
        Efixed, T0 = Eguess, computeT0(Eguess)
        
    logger.notice("Ei=%s, T=%s" % (Efixed,T0))

    #use detectors and first monitor to get Ei
    #result=GetEiMonDet(DetectorWorkspace="__IWS",MonitorWorkspace=__MonWS,EnergyGuess=Eguess,MonitorSpectrumNumber=1)
    #logger.notice("Ei=%s, T=%s" % (result[0], result[3]))
    #return [Eguess,result[0],result[3]]

    #Add other Filters here
    #Filter chopper 3 bad events
    #valC3=__MonWS.getRun()['Phase3'].getStatistics().median
    #FilterByLogValue(InputWorkspace='__IWS',OutputWorkspace='__IWS',LogName='Phase3',MinimumValue=valC3-0.15,MaximumValue=valC3+0.15)
    #FilterBadPulses(InputWorkspace="__IWS",OutputWorkspace = "__IWS",LowerCutoff = 50)
    return Eguess,Efixed,T0, getEi_from_monitors_failed

def CheckPacks(inputWorkspace,outdir) :
    #check here for bad packs - added 2014-2-14 by JLN
    #load pack group file where detectors are grouped 128 pixels along the tube, and 8 pixels across tubes
    packgroupfile = '/SNS/ARCS/shared/groupingfiles/ARCS_Grouped_Banks.xml'
    GroupDetectors(inputWorkspace,OutputWorkspace='__IWSBanks',MapFile="/SNS/ARCS/shared/groupingfiles/ARCS_Grouped_Banks.xml")
    runnum=str(inputWorkspace.getRunNumber())   
    #create a list object to hold zero sum packs
    zero_packs=[]

    #loop through histograms in the grouped, summed workspace and look for zeros
    for j in range(mtd['__IWSBanks'].getNumberHistograms()) :		
        #get the value of summed counts from the pack
        packvals = mtd['__IWSBanks'].extractY()[j]		
        if packvals[0] == 0:
            #looping over histograms from zero, but pack id's start at 1
            #output j+1 to correct for this offset.
            zero_packs.append(str(j+1))
    DeleteWorkspace('__IWSBanks')

    #output to the file only if there are packs with zero counts
    if len(zero_packs) > 0:
        pack_file=open(outdir+'pack_report','a')
        pack_string = str.join(' ',zero_packs)
        pack_file.write("run {1} zero counts in packs: {0}".format(pack_string,runnum))
        pack_file.write("\n")
        pack_file.close()
 
  

def WS_clean():
    DeleteWorkspace('__IWS')
    DeleteWorkspace('__OWS')
    DeleteWorkspace('__VAN')
    DeleteWorkspace('__MonWS')
    
    

def reduceMono(
        DGSdict, Ei, T0, EnergyTransferRange, 
        HardMaskFile, groupingFile, IntegrationRange,
        NormalizedVanadiumEqualToOne, angle,
        outdir, outfile, clean, NXSPE_flag):
    DGSdict['SampleInputWorkspace']='__IWS'
    DGSdict['SampleInputMonitorWorkspace']='__MonWS'
    DGSdict['IncidentEnergyGuess']=Ei
    DGSdict['UseIncidentEnergyGuess']='1'
    DGSdict['TimeZeroGuess']=T0
    DGSdict['EnergyTransferRange']=EnergyTransferRange
    #DGSdict['EnergyTransferRange']=[-0.5*EGuess,0.01*EGuess,0.9*EGuess] #Energy Binning
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
    ConvertToDistribution(Workspace="__OWS") 	                           #Divide by bin width

    if NXSPE_flag:            
        SaveNXSPE(InputWorkspace="__OWS", Filename= outdir+outfile+".nxspe",Efixed=Ei,Psi=angle,KiOverKfScaling=True) 

    #plots  
    #Update ConvertToMDHelper to new algorithm name per mandtid changeset 9396 - JLN 2014-8-13
    #minvals,maxvals=ConvertToMDHelper('__OWS','|Q|','Direct')
    minvals,maxvals=ConvertToMDMinMaxGlobal('__OWS','|Q|','Direct')
    xmin=minvals[0]
    xmax=maxvals[0]
    xstep=(xmax-xmin)*0.01
    ymin=minvals[1]
    ymax=maxvals[1]
    ystep=(ymax-ymin)*0.01
    x=arange(xmin,xmax,xstep)[0:100]
    y=arange(ymin,ymax,ystep)[0:100]
    Y,X=meshgrid(y,x)

    MD=ConvertToMD('__OWS',QDimensions='|Q|',dEAnalysisMode='Direct',MinValues=minvals,MaxValues=maxvals)
    ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
    ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
    MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
    d=MDH.getSignalArray()
    ne=MDH.getNumEventsArray()
    dne=d/ne

    # make a plot
    Zm=ma.masked_where(ne==0,dne)
    #pcm=pcolormesh(X,Y,log(Zm),shading='gouraud')
    #colorbar(pcm)
    #xlabel('|Q| ($\AA^{-1}$)')
    #ylabel('E (meV)')
    #title("Run "+outfile)
    #savefig(str(outdir+outfile+".nxs.png"),bbox_inches='tight')

    try:
        from postprocessing.publish_plot import plot_heatmap
        Zm = np.log(np.transpose(Zm))
        run_number=str(mtd['__OWS'].getRunNumber())
        plot_heatmap(
            run_number, x.tolist(), y.tolist(), Zm.tolist(), 
            x_title=u'|Q| (1/\u212b)', y_title='E (meV)',
            x_log=False, y_log=False, instrument='ARCS', publish=True)
    except:
        logger.error("Could not plot")

    if clean:
        WS_clean()
    return
