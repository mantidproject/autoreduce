#!/usr/bin/env python

import os, sys, numpy
#sys.path.append("/opt/Mantid/bin")
sys.path.append("/opt/mantidnightly/bin")

from mantid.simpleapi import *
from ARLibrary import *
from simpleflock import SimpleFlock
numpy.seterr(all='ignore')
import warnings
warnings.filterwarnings('ignore',module='numpy')


def do_reduction(filename,output_dir):
    instrument = 'HYS'
    #norm_file = '/SNS/HYS/shared/autoreduce/V_15meV_Sep2016.nxs'
    norm_file = '/SNS/HYS/shared/autoreduce/V_Apr17-2017.nxs'

    config['default.facility'] = "SNS"
    data = LoadEventNexus(filename)
    #data = ShiftLogTime(data,LogName = 'proton_charge', IndexShift = -1)  #needs to be checked each cycle
    if len(CheckForSampleLogs(Workspace = data, LogNames = 'pause')) == 0:
        data = FilterByLogValue(InputWorkspace = data, LogName = 'pause', MinimumValue = '-1',MaximumValue = '0.5')
    #data = FilterBadPulses(InputWorkspace = data, LowerCutoff = '5.')
    run_number = str(data.getRunNumber())
    out_prefix = instrument + "_" + run_number
    nxs_filename = os.path.join(output_dir,"event/" + out_prefix + "_events.nxs")
    nxspe_filename1 = os.path.join(output_dir, "4pixel/" + out_prefix + "_4pixel.nxspe")
    nxspe_filename2 = os.path.join(output_dir, "msk_tube/" + out_prefix + "_msk_tube.nxspe")


    # Check for sample logs
    checkResult = CheckForSampleLogs(Workspace=data, LogNames='s1, s2, msd, EnergyRequest, psr, psda, BL14B:Mot:Sample:Axis2,omega') 
    if len(checkResult):
        raise ValueError(checkResult)
    elog=ExperimentLog()
    elog.setLogList('s2,FermiSpeed,EnergyRequest,psr,psda,FlipOn')
    elog.setSimpleLogList('s2,FermiSpeed,EnergyRequest,psr,psda,FlipOn')
    elog.setSERotOptions('omega')
    elog.setSETempOptions('SampleTemp, sampletemp, SensorB,SensorB340')
    elog.setFilename(output_dir+'experiment_log.csv')
    elog.save_line(data.name())  

    run_obj = data.getRun()
    Ei = run_obj['EnergyRequest'].getStatistics().mean
    s1 = run_obj['omega'].getStatistics().mean

    # Work out some energy bins
    emin = -2.0 * Ei
    emin = -60.0 # temporary
    emax = Ei * 0.95
    if Ei > 10.0:
        emin = -30.0
    if Ei > 3.0:
        estep = 0.02
    if Ei > 4.9:
        estep = 0.05
    if Ei > 9.9:
        estep = 0.1
    if Ei > 19.9:
        estep = 0.2
    if Ei > 29.0:
        estep = 0.25
    if Ei > 39.0:
        estep = 0.5
    #move 0 meV energy transfer to a bin center
    emin = (int(emin/estep)+0.5)*estep
    energy_bins = "%f,%f,%f" % (emin, estep, emax)
      
    #get msd
    msd = run_obj['msd'].getStatistics().mean
    #get tofmin and tofmax, and filter out anything else
    tel = (39000+msd+4500)*1000/numpy.sqrt(Ei/5.227e-6)
    tofmin = tel-1e6/120-470
    tofmax = tel+1e6/120+470
    data = CropWorkspace(InputWorkspace = data, XMin = tofmin, XMax = tofmax)
      
    # Rotate instrument for polarized operations.
    additional_pars={}
    psda=run_obj['psda'].getStatistics().mean
    psr=run_obj['psr'].getStatistics().mean
    offset=psda*(1.-psr/4200.)
    if int(run_number) in range(160163,163120):
        offset*=-1.
    if offset!=0:
        RotateInstrumentComponent(Workspace=data,ComponentName='Tank',X=0, Y=1,Z=0,Angle=offset,RelativeRotation=1)
        IntegratedIncoh = Load(norm_file)
        additional_pars['UseProcessedDetVan'] = 1 
        additional_pars['DetectorVanadiumInputWorkspace'] = IntegratedIncoh   
    
    #TIB limits
    if Ei==15:
        tib=[22000.,23000.]
    else:
        tib = SuggestTibHYSPEC(Ei)
    
    MaskBTP(data,Pixel="1-8,121-128")
    #MaskBTP(data,Bank="20",Tube="6-8")

    #data for new normalization
    dgs,_=DgsReduction(SampleInputWorkspace=data,
                       IncidentEnergyGuess=Ei,
                       SampleInputMonitorWorkspace=data,
                       IncidentBeamNormalisation='None', 
                       TimeIndepBackgroundSub='1', 
                       TibTofRangeStart=tib[0], 
                       TibTofRangeEnd=tib[1],
                       SofPhiEIsDistribution='0')
    SaveNexus(Filename=nxs_filename, InputWorkspace=dgs)

    #4 pixel nxspe
    dgs4,_=DgsReduction(SampleInputWorkspace=data,
                        IncidentEnergyGuess=Ei,
                        EnergyTransferRange=energy_bins,
                        SampleInputMonitorWorkspace=data,
		                GroupingFile='/SNS/HYS/shared/autoreduce/4x1pixels.xml',  
		                IncidentBeamNormalisation='ByCurrent',
		                TimeIndepBackgroundSub='1',
		                TibTofRangeStart=tib[0],
		                TibTofRangeEnd=tib[1],
		                **additional_pars)
    SaveNXSPE(Filename=nxspe_filename1, InputWorkspace=dgs4, Psi=str(s1), KiOverKfScaling='1')
    #try to merge MD into sets
    try:
        comment=dgs4.getRun()['file_notes'].value.strip().replace(' ','_')
        if comment!='':
            UB_DAS=dgs4.getRun()['BL14B:CS:UBMatrix'].value[0]
            SetUB(dgs4,UB=UB_DAS)
            minValues,maxValues=ConvertToMDMinMaxGlobal(dgs4,
                                                        QDimensions='Q3D',
                                                        dEAnalysisMode='Direct',
                                                        Q3DFrames='HKL')
            mdpart=ConvertToMD(dgs4,
                               QDimensions='Q3D',
                               dEAnalysisMode='Direct',
                               Q3DFrames="HKL",
                               QConversionScales="HKL",
                               MinValues=minValues,
                               MaxValues=maxValues)
            #try to load the corresponding dataset and add to it
            filenameMD=os.path.join(output_dir, "sqw/" + comment + "_MD.nxs")
            with SimpleFlock("/SNS/users/inelastic/HYSPEC/locks/"+comment,3600):
                if os.path.isfile(filenameMD):
                    mdacc=LoadMD(filenameMD)
                    mdpart=MergeMD("mdpart,mdacc")
                SaveMD(mdpart,Filename=filenameMD)
    except Exception as e:
        logger.error("Something bad occured during MD processing")
        logger.error(repr(e))
        
    #tube nxspe
    MaskBTP(data,Pixel="1-40,89-128")
    #MaskBTP(data,Bank="20",Tube="6-8")
    dgst,_=DgsReduction(SampleInputWorkspace=data,
                        IncidentEnergyGuess=Ei,
                        EnergyTransferRange=energy_bins,
                        SampleInputMonitorWorkspace=data,
		                GroupingFile='/SNS/HYS/shared/autoreduce/128x1pixels.xml',  
		                IncidentBeamNormalisation='ByCurrent',
		                TimeIndepBackgroundSub='1',
		                TibTofRangeStart=tib[0],
		                TibTofRangeEnd=tib[1],
		                HardMaskFile='/SNS/HYS/shared/autoreduce/TubeTipMask.xml',
		                **additional_pars)
    SaveNXSPE(Filename=nxspe_filename2, InputWorkspace=dgst, Psi=str(s1), KiOverKfScaling='1')

    #make and publish image
    try:
        from postprocessing.publish_plot import plot_heatmap
        minvals,maxvals=ConvertToMDMinMaxLocal(dgs4,'|Q|','Direct')
        xmin=minvals[0]
        xmax=maxvals[0]
        xstep=(xmax-xmin)*0.01
        ymin=minvals[1]
        ymax=maxvals[1]
        ystep=(ymax-ymin)*0.01
        x=numpy.arange(xmin,xmax,xstep)
        y=numpy.arange(ymin,ymax,ystep)
        Y,X=numpy.meshgrid(y,x)

        MD=ConvertToMD(dgs4,
                       QDimensions='|Q|',
                       dEAnalysisMode='Direct',
                       MinValues=minvals,
                       MaxValues=maxvals)
        ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
        ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
        MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
        d=MDH.getSignalArray()
        ne=MDH.getNumEventsArray()
        dne=d/ne

        Zm=numpy.ma.masked_where(ne==0,dne)
        Zm = numpy.log(numpy.transpose(Zm))
        plot_heatmap(run_number, x.tolist(), y.tolist(), Zm.tolist(), x_title=u'|Q| (1/\u212b)', y_title='E (meV)',
                     x_log=False, y_log=False, instrument='HYS', publish=True)
    except Exception as e:
        logger.error("Something bad occured during the image processing")
        logger.error(repr(e))

    
if __name__ == "__main__":
    #check number of arguments
    if (len(sys.argv) != 3):
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
        path = sys.argv[1]
        out_dir = sys.argv[2]
        check_newer_script('HYS',out_dir)
        do_reduction(path, out_dir)

