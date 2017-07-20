#!/usr/bin/env python
from reduction_utils import *
   
if __name__ == "__main__":
    numpy.seterr("ignore")#ignore division by 0 warning in plots
    #processing parameters
     # Updated vanadium run 2014-12-15 - DLA
    RawVanadium="/SNS/ARCS/IPTS-19579/data/ARCS_95835_event.nxs"
    ProcessedVanadium="/SNS/ARCS/shared/autoreduce/vanadium_files/van95835.nxs"
    HardMaskFile=''
    IntegrationRange=[0.35,0.75] #integration range for Vanadium in angstroms
    MaskBTPParameters=[]
    #MaskBTPParameters=[{'Pixel':"1-7,122-128"}]
    #MaskBTPParameters.append({'Bank':"70",'Pixel':"1-12,117-128"})
    #MaskBTPParameters.append({'Bank':"71",'Pixel':"1-14,115-128"})
    #MaskBTPParameters.append({'Bank':"10",'Tube':"6"}) # mask for bad tube 2014-10-20 - DLA
    #MaskBTPParameters.append({'Bank':"27"}) # mask for bad pack (HV problem) 2014-10-20 - DLA
    MaskBTPParameters.append({'Pixel': '1-7,122-128'})
    MaskBTPParameters.append({'Pixel': '1-12,117-128', 'Bank': '70'})
    MaskBTPParameters.append({'Pixel': '1-14,115-128', 'Bank': '71'})
    MaskBTPParameters.append({'Pixel': '59-69', 'Bank': '99'})


    #groupingFile='/SNS/ARCS/shared/autoreduce/ARCS_2X1_grouping.xml'  #this is the grouping file, powder.xml, 2X1.xml and so on. needs the full path for this file.
    #groupingFile='/SNS/ARCS/shared/autoreduce/ARCS_4X2_grouping.xml'  #this worked for smaller files DLA
    groupingFile="/SNS/ARCS/shared/autoreduce/ARCS_2X1_grouping.xml"
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
        outdir = sys.argv[2]+'/'
        if not os.path.exists(outdir): os.makedirs(outdir)

    [EGuess,Ei,T0, getEi_from_monitors_failed]=preprocessData(filename)
    elog=ExperimentLog()
    elog.setLogList('vChTrans,Speed1,Phase1,Speed2,Phase2,Speed3,Phase3,EnergyRequest,s1t,s1r,s1l,s1b,s2t,s2r,s2l,s2b')
    elog.setSimpleLogList("vChTrans, EnergyRequest, s1t, s1r, s1l, s1b,s2t,s2r,s2l,s2b")
    elog.setSERotOptions('Mag05Rot, CCR12Rot, SEOCRot, CCR16Rot, SEHOT11, micas70mmRot,SE70mmRot')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorA, SensorB, SensorC, SensorD')
    elog.setFilename(outdir+'experiment_log.csv')
    angle=elog.save_line('__MonWS',CalculatedEi=Ei,CalculatedT0=T0)  

    #added to check the file for zero-summed packs in the event of a detector failure.
    # JLN 2014-2-14
    CheckPacks(mtd['__IWS'],outdir)

    outpre='ARCS'
    runnum=str(mtd['__IWS'].getRunNumber()) 
    outfile=outpre+'_'+runnum+'_autoreduced'  
    if not math.isnan(Ei):
        # monochromatic reduction
        processed_van_file = ProcessedVanadium
        if not os.path.isabs(processed_van_file):
            processed_van_file = os.path.join(outdir, ProcessedVanadium)
        DGSdict=preprocessVanadium(RawVanadium, processed_van_file, MaskBTPParameters)

        EnergyTransferRange = [-0.5*EGuess,0.01*EGuess,0.95*EGuess] #Energy Binning
        reduceMono(
            DGSdict, Ei, T0, EnergyTransferRange, 
            HardMaskFile, groupingFile, IntegrationRange,
            NormalizedVanadiumEqualToOne, angle,
            outdir, outfile, clean, NXSPE_flag)

    else:  #Do this if it is whitebeam
        ConvertUnits(InputWorkspace="__IWS",OutputWorkspace="__IWS",Target='dSpacing')
        Rebin(InputWorkspace="__IWS",OutputWorkspace="__OWS",Params='0.1,0.005,5',PreserveEvents='0')
        SaveNexus(InputWorkspace="__OWS", Filename= outdir+outfile+".nxs")                                                 

    if getEi_from_monitors_failed:
        raise ValueError("Warning: getEi from monitor data failed. Used EnergyRequest and calculated T0 accordingly")
