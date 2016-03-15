#!/usr/bin/env python

#imports section
import sys, os, glob, filecmp, datetime, shutil
sys.path.append("/SNS/CNCS/shared/autoreduce")
from ARLibrary import * #note that ARLibrary would set mantidpath as well
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *

#parameters section
#this part changes with web input
MaskBTPParameters=[]
MaskBTPParameters.append({'Pixel': '1-43,95-128'})
#MaskBTPParameters.append({'Pixel': '1-7,122-128'})
MaskBTPParameters.append({'Bank': '36-50'})#8T magnet
raw_vanadium="/SNS/CNCS/IPTS-16111/1/161099/NeXus/CNCS_161099_event.nxs"
processed_vanadium="van161099.nxs"
grouping="2x1" #allowed values 1x1, 2x1, 4x1, 8x1, powder
Emin="-0.5"
Emax="0.95"
Estep="0.005"
E_pars_in_mev=False
TIB_min=""
TIB_max=""
T0=""
Motor_names='huber,SERotator2,OxDilRot,CCR13VRot,SEOCRot,CCR10G2Rot,Ox2WeldRot,ThreeSampleRot'
Temperature_names='SampleTemp,sampletemp,SensorC,SensorB,SensorA,temp5,temp8'
create_elastic_nxspe=True #+-0.1Ei, 5 steps
create_MDnxs=False
a=""
b=""
c=""
alpha=""
beta=""
gamma=""
uVector=""
vVector=""

#parameters not on the webpage
#below remains unchanged
VanadiumIntegrationRange=[84000.0,94000.0]#integration range for Vanadium in TOF at 1.0 meV
NormalizedVanadiumEqualToOne = True




#Reduction section
def check_newer_script(instrument,folder):
    """
    Checks if reduce_instrument.py is in a certain folder.
    It searches for all reduce_instrument*.py, takes the newest one and compares the content with
    /SNS/instrument/shared/autoreduce/reduce_instrument.py. If there is no such file in the folder,
    or the content has changed, it will copy reduce_instrument.py to reduce_instrument_date_and_time.py
    in folder.
    """
    master_filename="/SNS/"+instrument+"/shared/autoreduce/reduce_"+instrument+".py"
    #master_filename='/SNS/users/3y9/Desktop/reduce_CNCS.py'
    search_pattern=os.path.join(folder,"reduce_"+instrument+"*.py")
    result=glob.glob(search_pattern)
    newer_file_exists=True
    if result:
        # there are reduce_... files, get the newest
        newest_filename=max(result,key=os.path.getctime)
        #check content. If the same, then there is no newer file
        newer_file_exists=not filecmp.cmp(master_filename,newest_filename)
    if newer_file_exists:
        new_filename=os.path.join(folder,"reduce_"+instrument+"_"+datetime.datetime.now().strftime('%Y.%m.%d_%H.%M.%S')+".py")
        shutil.copy2(master_filename,new_filename)


def preprocessVanadium(Raw,Processed,Parameters):
    if os.path.isfile(Processed):
        LoadNexus(Filename=Processed,OutputWorkspace="__VAN")
        dictvan={'UseProcessedDetVan':'1','DetectorVanadiumInputWorkspace':'__VAN'}
    else:
        LoadEventNexus(Filename=Raw,OutputWorkspace="__VAN",Precount=0)
        for d in Parameters:
            MaskBTP(Workspace="__VAN",**d)
        dictvan={'SaveProcessedDetVan':'1',
                 'DetectorVanadiumInputWorkspace':'__VAN',
                 'SaveProcDetVanFilename':Processed,
                 'UseBoundsForDetVan':'1',
                 'DetVanIntRangeHigh':VanadiumIntegrationRange[1],
                 'DetVanIntRangeLow':VanadiumIntegrationRange[0],
                 'DetVanIntRangeUnits':'TOF'}
    return dictvan

def preprocessData(filename):
    dictdata={}    
    __IWS=LoadEventNexus(filename)
    Ei=__IWS.getRun()['EnergyRequest'].firstValue()
    t0=preprocesst0(Ei,__IWS)
    tibmin,tibmax=preprocessTIB(Ei,__IWS)
    ETransfer=preprocessEnergyTransfer(Ei)
    dictdata['SampleInputWorkspace']='__IWS'
    dictdata['SampleInputMonitorWorkspace']='__IWS'
    dictdata['UseIncidentEnergyGuess']='1'
    dictdata['IncidentEnergyGuess']=Ei
    dictdata['TimeZeroGuess']=t0
    dictdata['EnergyTransferRange']=ETransfer
    dictdata['TimeIndepBackgroundSub']=True
    dictdata['TibTofRangeStart']=tibmin
    dictdata['TibTofRangeEnd']=tibmax
    dictdata['IncidentBeamNormalisation']='ByCurrent'
    return dictdata

#import numpy as np
#def preprocesst0(Eguess,ws):
#    try:
#        t0=float(T0)
#    except ValueError:
#        mode=ws.run()['DoubleDiskMode'].timeAverageValue()
#        Ei=ws.run()['EnergyRequest'].timeAverageValue()
#        lnEi=np.log(Ei)
#        t0=157.539+lnEi*(-33.04593+lnEi*(-8.07523+lnEi*(2.2143-0.109521767*lnEi)))
#        if (mode!=1):
#            t0-=5.91
#    AddSampleLog(Workspace=ws,LogName="CalculatedT0",LogText=str(t0),LogType="Number")
#    return t0

def preprocesst0(Eguess,ws):
    try:
        t0=float(T0)
    except ValueError:
        mode=ws.run()['DoubleDiskMode'].timeAverageValue()
        if (mode==1):
            _Ei,_FMP,_FMI,t0=GetEi(ws)
        else:
            t0=-5.91
    AddSampleLog(Workspace=ws,LogName="CalculatedT0",LogText=str(t0),LogType="Number")
    return t0

def preprocessTIB(EGuess,ws):
    try:
        tibmin=float(TIB_min)
        tibmax=float(TIB_max)
    except ValueError:
        if EGuess<50:
            tibmin,tibmax=SuggestTibCNCS(EGuess)
        else:
            tibmin=5000
            tibmax=15000
        if (abs(EGuess-12)<0.1):
            tibmin,tibmax=[20500.0,21500.0]
        if (abs(EGuess-25)<0.1):
            tibmin,tibmax=[11000.0,15000.0]  
    AddSampleLogMultiple(ws,"TIBmin,TIBmax",str(tibmin)+','+str(tibmax))
    return (tibmin,tibmax)

def preprocessEnergyTransfer(EGuess):
    try:
        emin=float(Emin)
        emax=float(Emax)
        estep=float(Estep)
        if E_pars_in_mev:
            return [emin,estep,emax]
        else:
            return [emin*EGuess,estep*EGuess,emax*EGuess]
    except ValueError:
        return [-0.5*EGuess,0.01*EGuess,0.95*EGuess]

def preprocessGrouping(ws,outdir):
    if grouping in ['2x1', '4x1', '8x1']:
        dictgrouping={'GroupingFile':"/SNS/CNCS/shared/autoreduce/CNCS_"+grouping+".xml"}
    elif grouping=='powder':
        GenerateGroupingPowder(InputWorkspace=ws,AngleStep=0.5, GroupingFilename=outdir+'powdergroupfile.xml')
        dictgrouping={'GroupingFile':outdir+'powdergroupfile.xml'}
    else:
        dictgrouping={'GroupingFile':''}
    return dictgrouping




if __name__ == "__main__":    
    #check number of arguments
    if (len(sys.argv) != 3): 
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()

    config['default.facility']="SNS"
    nexus_file=sys.argv[1]
    output_directory=sys.argv[2]
    
    check_newer_script("CNCS",output_directory)
    
    DGSdict=preprocessVanadium(raw_vanadium,output_directory+processed_vanadium,MaskBTPParameters)
    datadict=preprocessData(nexus_file)
    groupdict=preprocessGrouping("__IWS",output_directory)
    DGSdict.update(datadict)
    DGSdict.update(groupdict)
    DGSdict['OutputWorkspace']='reduce'

    DgsReduction(**DGSdict)

    if DGSdict.has_key('SaveProcessedDetVan') and NormalizedVanadiumEqualToOne:
        filename=DGSdict['SaveProcDetVanFilename']
        os.chmod(filename,0664)
        LoadNexus(Filename=filename,OutputWorkspace="__VAN")
        datay = mtd['__VAN'].extractY()
        meanval = float(datay[datay>0].mean())
        CreateSingleValuedWorkspace(OutputWorkspace='__meanval',DataValue=meanval)
        Divide(LHSWorkspace='__VAN',RHSWorkspace='__meanval',OutputWorkspace='__VAN') #Divide the vanadium by the mean
        Multiply(LHSWorkspace='reduce',RHSWorkspace='__meanval',OutputWorkspace='reduce') #multiple by the mean of vanadium Normalized data = Data / (Van/meanvan) = Data *meanvan/Van
        SaveNexus(InputWorkspace="__VAN", Filename= filename) 
        os.chmod(filename,0664)

    if create_elastic_nxspe:
        DGSdict['OutputWorkspace']='reduce_elastic'
        EGuess=DGSdict['IncidentEnergyGuess']
        DGSdict['EnergyTransferRange']=[-0.1*EGuess,0.04*EGuess,0.1*EGuess]
        DgsReduction(**DGSdict)

    elog=ExperimentLog()
    elog.setLogList('EnergyRequest,CalculatedT0,TIBmin,TIBmax')
    elog.setSimpleLogList("EnergyRequest,CalculatedT0,TIBmin,TIBmax")
    elog.setSERotOptions(Motor_names)
    elog.setSETempOptions(Temperature_names)
    elog.setFilename(output_directory+'experiment_log.csv')


    run_number =mtd["reduce"].getRun()['run_number'].value
    if groupdict['GroupingFile']==output_directory+'powdergroupfile.xml':
        nxspe_filename=os.path.join(output_directory, "CNCS_" + run_number + "_powder.nxspe")
        SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce", Psi="0", KiOverKfScaling='1',ParFile=output_directory+'powdergroupfile.par')
        os.chmod(nxspe_filename,0664)
        if create_elastic_nxspe:
            nxspe_filename=os.path.join(output_directory, "elastic/CNCS_" + run_number + "_elastic_powder.nxspe")
            SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce_elastic", Psi="0", KiOverKfScaling='1',ParFile=output_directory+'powdergroupfile.par')
            os.chmod(nxspe_filename,0664)
    else:
        s1=elog.save_line('reduce')
        roundedvalue = "%.1f" % s1
        valuestringwithoutdot = str(roundedvalue).replace('.', 'p')
        nxspe_filename=os.path.join(output_directory, "CNCS_" + run_number + "_" + valuestringwithoutdot + ".nxspe")
        SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce", Psi=str(s1), KiOverKfScaling='1')     
        os.chmod(nxspe_filename,0664)
        if create_elastic_nxspe:
            nxspe_filename=os.path.join(output_directory, "elastic/CNCS_" + run_number + "_" + valuestringwithoutdot + "_elastic.nxspe")
            SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce_elastic", Psi="0", KiOverKfScaling='1')
            os.chmod(nxspe_filename,0664)

