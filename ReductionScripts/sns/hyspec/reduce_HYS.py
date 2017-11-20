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
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt 


def CorrectTransmissionPolarizer(WS,EFixed):
	#DeltaE-Ei=-Ef
	WS=ScaleX(WS,Factor=-EFixed,Operation="Add")
	WS=ExponentialCorrection(WS,C0=1/0.585,C1=1/10.77,Operation="Multiply") #was 58.5% *exp(-Ef/12.07)
	WS=ScaleX(WS,Factor=EFixed,Operation="Add")
	return WS

def generate_slice(ws,mdh_base_filename,extra_name,ad0,ad1,ad2,ad3):
    filenameMD_data=mdh_base_filename+extra_name+"_data.nxs"
    filenameMD_norm=mdh_base_filename+extra_name+"_norm.nxs"
    if mtd.doesExist('mdh_data'):
        DeleteWorkspace('mdh_data')
    if mtd.doesExist('mdh_norm'):
        DeleteWorkspace('mdh_norm')
    try:
        LoadMD(filenameMD_data,LoadHistory=False,OutputWorkspace='mdh_data')
        LoadMD(filenameMD_norm,LoadHistory=False,OutputWorkspace='mdh_norm')
    except:
        pass
    MDNormDirectSC(InputWorkspace=ws,
                   SkipSafetyCheck=True,
                   TemporaryDataWorkspace='mdh_data' if mtd.doesExist('mdh_data') else None,
                   TemporaryNormalizationWorkspace='mdh_norm' if mtd.doesExist('mdh_norm') else None,
                   AlignedDim0=ad0,
                   AlignedDim1=ad1,
                   AlignedDim2=ad2,
                   AlignedDim3=ad3,
                   OutputWorkspace='mdh_data',
                   OutputNormalizationWorkspace='mdh_norm')
    SaveMD('mdh_data', Filename=filenameMD_data)
    SaveMD('mdh_norm', Filename=filenameMD_norm)
    return (mtd['mdh_data'],mtd['mdh_norm'])
    
def do_reduction(filename,output_dir):
    instrument = 'HYS'
    norm_file = '/SNS/HYS/shared/autoreduce/Vrod_15meV_Nov17_2017.nxs'
    #norm_file = '/SNS/HYS/shared/autoreduce/V_3p8meV_Aug31_2017.nxs'

    correct_transmission=True

    config['default.facility'] = "SNS"
    data = LoadEventNexus(filename)
    #data = ShiftLogTime(data,LogName = 'proton_charge', IndexShift = -1)  #n 'BL14B:SE:Lakeshore:KRDG3'eeds to be checked each cycle
    if len(CheckForSampleLogs(Workspace = data, LogNames = 'pause')) == 0:
        data = FilterByLogValue(InputWorkspace = data, LogName = 'pause', MinimumValue = '-1',MaximumValue = '0.5')
    #data = FilterBadPulses(InputWorkspace = data, LowerCutoff = '5.')
    run_number = str(data.getRunNumber())
    out_prefix = instrument + "_" + run_number
    nxs_filename = os.path.join(output_dir,"event/" + out_prefix + "_events.nxs")
    nxspe_filename1 = os.path.join(output_dir, "4pixel/" + out_prefix + "_4pixel.nxspe")
    nxspe_filename2 = os.path.join(output_dir, "msk_tube/" + out_prefix + "_msk_tube.nxspe")
    mde_nxs_filename = os.path.join(output_dir,"mde/" + out_prefix + "_mde.nxs")
    mdh_base_filename = os.path.join(output_dir,"mdh/HYS_mdh_")

    # Check for sample logs
    checkResult = CheckForSampleLogs(Workspace=data, LogNames='s1, s2, msd, EnergyRequest, psr, psda, BL14B:Mot:Sample:Axis2,omega') 
    if len(checkResult):
        raise ValueError(checkResult)
    elog=ExperimentLog()
    elog.setLogList('s2,FermiSpeed,EnergyRequest,psr,psda,FlipOn')
    elog.setSimpleLogList('s2,FermiSpeed,EnergyRequest,psr,psda,FlipOn')
    elog.setSERotOptions('omega')
    elog.setSETempOptions('BL14B:SE:Lakeshore:KRDG3,SampleTemp, sampletemp, SensorB,SensorB340')
    elog.setFilename(output_dir+'experiment_log.csv')
    elog.save_line(data.name())  

    run_obj = data.getRun()
    Ei = run_obj['EnergyRequest'].getStatistics().mean
    s1 = run_obj['omega'].getStatistics().mean

    # Work out some energy bins
    emin = -2.0 * Ei
    #emin = -100.0 # temporary
    emax = Ei * 0.95
    if Ei > 10.0:
        emin = -40.0 #changed from -30 Nov 7 2017
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
                       EnergyTransferRange=energy_bins,
                       TimeIndepBackgroundSub='1', 
                       TibTofRangeStart=tib[0], 
                       TibTofRangeEnd=tib[1],
                       SofPhiEIsDistribution='0')
    dgs=CropWorkspace(InputWorkspace=dgs, XMin = emin, XMax = emax)
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
    if correct_transmission:
        dgs4c=CorrectTransmissionPolarizer(dgs4,Ei)
        dgs4=CloneWorkspace(dgs4c)
    SaveNXSPE(Filename=nxspe_filename1, InputWorkspace=dgs4, Psi=str(s1), KiOverKfScaling='1')
    #try to merge MD into sets
    try:
        comment=dgs.getRun()['file_notes'].value.strip().replace(' ','_')
        if comment!='' and comment!='(unset)' and ('powder' not in comment):
            #UB_DAS=dgs.getRun()['BL14B:CS:UBMatrix'].value[0]
            SetUB(dgs,a=6.12,b=6.12,c=6.12,alpha=90,beta=90,gamma=90,u="1,1,0",v="0,0,1")
            minValues,maxValues="-2.5,-1,-1,-1","2.5,4.5,1,16"
            
            mdpart=ConvertToMD(dgs,
                               QDimensions='Q3D',
                               dEAnalysisMode='Direct',
                               Q3DFrames="HKL",
                               QConversionScales="HKL",
                               MinValues=minValues,
                               MaxValues=maxValues,
                               UProj="1,1,0",
                               VProj="0,0,1",
                               WProj="1,-1,0")
            #try to load the corresponding dataset and add to it
            d,n=generate_slice(mdpart,mdh_base_filename,comment+"_HHL_0meV","[H,H,0],-2.5,2.5,200",
                               "[0,0,L],-1,4.5,250","DeltaE,-0.5,0.5,1","[H,-H,0],-0.5,0.5,1")
            DivideMD(d,n,OutputWorkspace='hhl')
            d1,n1=generate_slice(mdpart,mdh_base_filename,comment+"_HHE_L_3","[H,H,0],-2.5,1.5,300",
                               "DeltaE,0,14,100","[0,0,L],2.9,3.1,1","[H,-H,0],-0.5,0.5,1")
            DivideMD(d1,n1,OutputWorkspace='hh3E')
            d2,n2=generate_slice(mdpart,mdh_base_filename,comment+"_HHE_L_0","[H,H,0],-2.5,1.5,300",
                               "DeltaE,0,16,100","[0,0,L],-0.1,0.1,1","[H,-H,0],-0.5,0.5,1")
            DivideMD(d2,n2,OutputWorkspace='hh0E')
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
    if correct_transmission:
        dgst=CorrectTransmissionPolarizer(dgst,Ei)

    SaveNXSPE(Filename=nxspe_filename2, InputWorkspace=dgst, Psi=str(s1), KiOverKfScaling='1')

    #make and publish image
    try:
        from postprocessing.publish_plot import plot_heatmap, publish_plot
        minvals,maxvals=ConvertToMDMinMaxLocal(dgs4,'|Q|','Direct')
        minvals[0]=0.
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

        comment=dgs4.getRun()['file_notes'].value.strip().replace(' ','_')
        if ('powder' in comment):
            #this is not really an MDH, but an MDE from histogram
            #don't do it for short runs
            filenameMD_powder=mdh_base_filename+comment+".nxs"
            try:
                tempMD=LoadMD(filenameMD_powder,LoadHistory=False)
                MD+=tempMD
                ad0='|Q|,0,'+str(xmax)+',100'
            except:
                pass
            SaveMD(MD,Filename=filenameMD_powder)
        MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
        d=MDH.getSignalArray()
        ne=MDH.getNumEventsArray()
        dne=d/ne

        Zm=numpy.ma.masked_where(ne==0,dne)
        Zm = numpy.log(numpy.transpose(Zm))
        plot_html=''
        myplot=plot_heatmap(run_number, x.tolist(), y.tolist(), Zm.tolist(), x_title=u'|Q| (1/\u212b)', y_title='E (meV)',
                     x_log=False, y_log=False, instrument='HYS', publish=False)
        plot_html+="<div>{0}</div>\n".format(myplot)
      
        try:
            hhl=mtd['hhl']
            xmin=hhl.getDimension(0).getMinimum()
            xmax=hhl.getDimension(0).getMaximum()
            xstep=hhl.getDimension(0).getX(1)-xmin
            ymin=hhl.getDimension(1).getMinimum()
            ymax=hhl.getDimension(1).getMaximum()
            ystep=hhl.getDimension(1).getX(1)-ymin
            x=numpy.arange(xmin,xmax,xstep)
            y=numpy.arange(ymin,ymax,ystep)
            Y,X=numpy.meshgrid(y,x)
            darray=hhl.getSignalArray()[:,:,0,0]
            Zm=numpy.ma.masked_where(numpy.isnan(darray),darray)
            Zm = numpy.log(numpy.transpose(Zm))
            myplot1=plot_heatmap(run_number, x.tolist(), y.tolist(), Zm.tolist(), x_title='HH0', y_title='00L',
                     x_log=False, y_log=False, instrument='HYS', publish=False)
            plot_html+="<div>{0}</div>\n".format(myplot1)        
        except:
            pass

        try:
            hhE=mtd['hh3E']
            xmin=hhE.getDimension(0).getMinimum()
            xmax=hhE.getDimension(0).getMaximum()
            xstep=hhE.getDimension(0).getX(1)-xmin
            ymin=hhE.getDimension(1).getMinimum()
            ymax=hhE.getDimension(1).getMaximum()
            ystep=hhE.getDimension(1).getX(1)-ymin
            x=numpy.arange(xmin,xmax,xstep)
            y=numpy.arange(ymin,ymax,ystep)
            Y,X=numpy.meshgrid(y,x)
            darray=hhE.getSignalArray()[:,:,0,0]
            Zm=numpy.ma.masked_where(numpy.isnan(darray),darray)
            Zm = numpy.log(numpy.transpose(Zm))
            myplot2=plotdgs_heatmap(run_number, x.tolist(), y.tolist(), Zm.tolist(), x_title='HH3', y_title='E(meV)',
                     x_log=False, y_log=False, instrument='HYS', publish=False)
            plot_html+="<div>{0}</div>\n".format(myplot2)        
        except:
            pass
            
        try:
            lE=mtd['hh0E']
            xmin=lE.getDimension(0).getMinimum()
            xmax=lE.getDimension(0).getMaximum()
            xstep=lE.getDimension(0).getX(1)-xmin
            ymin=lE.getDimension(1).getMinimum()
            ymax=lE.getDimension(1).getMaximum()
            ystep=lE.getDimension(1).getX(1)-ymin
            x=numpy.arange(xmin,xmax,xstep)
            y=numpy.arange(ymin,ymax,ystep)
            Y,X=numpy.meshgrid(y,x)
            darray=lE.getSignalArray()[:,:,0,0]
            Zm=numpy.ma.masked_where(numpy.isnan(darray),darray)
            Zm = numpy.log(numpy.transpose(Zm))
            myplot3=plot_heatmap(run_number, x.tolist(), y.tolist(), Zm.tolist(), x_title='HH0', y_title='E(meV)',
                     x_log=False, y_log=False, instrument='HYS', publish=False)
            plot_html+="<div>{0}</div>\n".format(myplot3)        
        except:
            pass        
        publish_plot("HYS", run_number, files={'file': plot_html})  
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

