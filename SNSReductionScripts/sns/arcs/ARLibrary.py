#!/usr/bin/env python

import sys,os
sys.path.append("/opt/Mantid/bin")
from numpy import *
from string import *

import mantid

def MaskAngle(**kwargs):
    """
    Routine to mask angles in a given interval (in degrees)
    Required keyword Workspace
    Optional keywords twothetamin,twothetamax
    By default twothetamin=0, twothetamax=180, so if no keywords are set, all detectors are gouing to be masked
    Returns a list of detectors that were masked
    """
    workspace=kwargs.get('Workspace',None)
    if (workspace==None):
        raise RuntimeError("Workspace not set for angle mask")
    ttmin = (kwargs.get('twothetamin',0.0))
    ttmax = (kwargs.get('twothetamax',180.0))

    if ttmin== None:
        ttmin = 0.0
    if ttmax == None:
        ttmax = 180.0

    #check for silly angle ranges
    if ttmin < 0 :
        ttmin = 0
    if ttmax > 180 :
        ttmax =180

    if ttmin > ttmax :
        raise ValueError("ttmin > ttmax, please check angle range for masking")

    detlist=[]

    #get the number of spectra
    ws = mantid.mtd[workspace]
    numspec = ws.getNumberHistograms()
    #detlist=[]
    for i in range(numspec):
        det=ws.getDetector(i)
        if not det.isMonitor():
            tt=degrees(det.getTwoTheta(mantid.kernel.V3D(0,0,0),mantid.kernel.V3D(0,0,1)))
            if tt>= ttmin and tt<= ttmax:
                detlist.append(det.getID())

    if len(detlist)> 0:
        mantid.simpleapi.MaskDetectors(Workspace=workspace,DetectorList=detlist)
    else:
        print "no detectors within this range"
    return detlist
    
    
    
def _getEightPackHandle(inst,banknum):
    """
    Helper function to return the handle to a given eightpack
    """
    name=inst.getName()
    banknum=int(banknum)
    if name=="ARCS":
        if  (1<=banknum<= 38):
            return inst[3][banknum-1][0]
        elif(39<=banknum<= 77):
            return inst[4][banknum-39][0]
        elif(78<=banknum<=115):
            return inst[5][banknum-78][0]
        else: 
            raise ValueError("Out of range index for ARCS instrument bank numbers")
    elif name=="CNCS":
        if  (1<=banknum<= 50):
            return inst[3][banknum-1][0]
        else: 
            raise ValueError("Out of range index for CNCS instrument bank numbers")
    elif name=="HYSPEC":
        if  (1<=banknum<= 20):
            return inst[3][banknum-1][0]  
        else: 
            raise ValueError("Out of range index for HYSPEC instrument bank numbers")
    elif name=="SEQUOIA":
        if  (38<=banknum<= 74):
            return inst[3][banknum-38][0]
        elif(75<=banknum<= 113):
            return inst[4][banknum-75][0]
        elif(114<=banknum<=150):
            return inst[5][banknum-114][0]
        else: 
          raise ValueError("Out of range index for SEQUOIA instrument bank numbers")
          
          
          
def _parseBTPlist(value):
    """
    Helper function to transform a string into a list of integers
    For example "1,2-4,8-10" will become [1,2,3,4,8,9,10]
    It will deal with lists as well, so range(1,4) will still be [1,2,3]
    """
    runs = []
    #split the commas
    parts = str(value).strip(']').strip('[').split(',')
    #now deal with the hyphens
    for p in parts:
        if len(p) > 0:
            elem = p.split("-")
        if len(elem) == 1:
            runs.append(int(elem[0]))
        if len(elem) == 2:
            startelem = int(elem[0])
            endelem   = int(elem[1])
            if endelem < startelem:
                raise ValueError("The element after the hyphen needs to be greater or equal than the first element")
            elemlist  = range(startelem,endelem+1)
            runs.extend(elemlist)
    return runs          
           
           
           
def MaskBTP(**kwargs):
    """
    Function to mask banks, tubes, and pixels, on ARCS, CNCS, HYSPEC, or SEQUOIA
    Keywords:
    Instrument: not necessary if Workspace keyword is set
    Bank: a string or list. Acceptable format "1,3-5,7-9" means banks 1,3,4,5,7,8,9. If empty, it will apply to all banks
    Tube: same as bank
    Pixel: same as bank
    Workspace: a workspace to mask. If empty, and Instrument keyword is given a workspace called TemporaryWS will be created
    Returns the list of pixels masked 
    """
    instrument=kwargs.get('Instrument',None)
    banks=kwargs.get('Bank',None)
    tubes=kwargs.get('Tube',None)
    pixels=kwargs.get('Pixel',None)
    workspace=kwargs.get('Workspace',None)
    detlist=[]
    try:
        instrument=mantid.mtd[workspace].getInstrument().getName()
    except:
        pass
    instrumentList=["ARCS","CNCS","HYSPEC","SEQUOIA"]
    try:
        instrumentList.index(instrument)
    except:
        raise ValueError("Instrument not found")
        return detlist
    if (workspace==None):
        IDF=mantid.api.ExperimentInfo.getInstrumentFilename(instrument)
        workspace='TemporaryWS'
        instrument=mantid.simpleapi.LoadEmptyInstrument(IDF,OutputWorkspace=workspace).getInstrument().getName()
    if (banks==None):
        if (instrument=="ARCS"):
            banks=arange(115)+1
        elif (instrument=="CNCS"):
            banks=arange(50)+1
        elif (instrument=="HYSPEC"):
            banks=arange(20)+1
        elif (instrument=="SEQUOIA"):
            banks=arange(113)+38
    else:
        # try to get the bank numbers in an array, even if the banks is string, array, or an integer
        banks=_parseBTPlist(banks)
        try:
            len(banks)
        except:
            banks=[banks]
    if(tubes==None):
        tubes=arange(8)+1
    else:
        tubes=_parseBTPlist(tubes)
        try:
            len(tubes)
        except:
            tubes=[tubes]
    if(pixels==None):
        pixels=arange(128)+1
    else:
        pixels=_parseBTPlist(pixels)
        try:
            len(pixels)
        except:
            pixels=[pixels]  
    for b in banks:
        ep=_getEightPackHandle(mantid.mtd[workspace].getInstrument(),b)
        for t in tubes:
            if ((t<1) or (t>8)):
                raise ValueError("Out of range index for tube number")
            else:
                for p in pixels:
                    if ((p<1) or (p>128)):
                        raise ValueError("Out of range index for pixel number")
                    else:
                        pid=ep[int(t-1)][int(p-1)].getID()
                        detlist.append(pid)
    mantid.simpleapi.MaskDetectors(Workspace=workspace,DetectorList=detlist)
    return detlist    



class ExperimentLog(object):
    def __init__(self):
        self.log_list=[]
        self.simple_logs=[]
        self.SERotOptions=[]
        self.SETempOptions=[]
        self.firstLine=''
        self.Filename=''
        self.kwds=[]
                
    def setLogList(self,logstring):
        self.log_list=[a.strip() for a in logstring.split(',')]
        
    def setSimpleLogList(self,logstring):
        self.simple_logs=[a.strip() for a in logstring.split(',')] 
    
    def setFilename(self,fname):
        self.Filename=fname
        
    def setSERotOptions(self,logstring):
        self.SERotOptions=[a.strip() for a in logstring.split(',')]  
               
    def setSETempOptions(self,logstring):
        self.SETempOptions=[a.strip() for a in logstring.split(',')]     
                     
    def log_line_gen(self,IWSName):
        """
        IWSName is a string of the workspace name
        """
        ws=mantid.mtd[IWSName]
        parameterList=[]
        self.firstLine+='RunNumber, '
        parameterList.append(str(ws.getRunNumber()))                                    #run number
        self.firstLine+='Title, '
        parameterList.append(ws.getTitle().replace(' ','_').replace(',','_'))           #title - spaces and commas are replaced by underscores
        self.firstLine+='Comment, '
        parameterList.append(ws.getComment().replace(' ','_').replace(',','_'))         #comment from the file - spaces and commas with underscores
        self.firstLine+='StartTime, '
        parameterList.append(ws.getRun()['start_time'].value)                           #start time
        self.firstLine+='EndTime, '
        parameterList.append(ws.getRun()['end_time'].value)                             #end time
        self.firstLine+='Duration, '
        parameterList.append(str(ws.getRun()['duration'].value))                        #duration
        self.firstLine+='ProtonCharge, '
        parameterList.append(str(ws.getRun().getProtonCharge()))                        #proton charge in microamps*hour
                
        for sLog in self.log_list:
            if ws.getRun().hasProperty(sLog):
                try: #check if it's a time series property
                    stats=ws.getRun()[sLog].getStatistics()
                    if sLog in self.simple_logs:
                        self.firstLine+='%s mean,'%(sLog)
                        parameterList.append(str(stats.mean))
                    else:
                        self.firstLine+='%s mean,%s minimum,%s maximum,%s stddev,'%(sLog,sLog,sLog,sLog)
                        parameterList.append(str(stats.mean))
                        parameterList.append(str(stats.minimum))
                        parameterList.append(str(stats.maximum))
                        parameterList.append(str(stats.standard_deviation))
                except: #not a TSP
                    self.firstLine+='%s,'%(sLog)
                    parameterList.append(ws.getRun()[sLog].valueAsStr)
            else: #could not find that parameter
                if sLog in self.simple_logs:
                    self.firstLine+='%s ,'%(sLog)
                    parameterList.append('N/A')
                else:   
                    self.firstLine+='%s mean,%s minimum,%s maximum,%s stddev,'%(sLog,sLog,sLog,sLog)
                    parameterList.append('N/A')
                    parameterList.append('N/A')
                    parameterList.append('N/A')
                    parameterList.append('N/A')
        

  
        #check for sample environment temperature reading
        for SET in self.SETempOptions:
            if SET not in self.log_list:  #make sure not to write again, if it was in log_list 
                if ws.getRun().hasProperty(SET):
                    self.log_list.append(SET) #next time is in the log_list
                    stats=ws.getRun().getProperty(SET).getStatistics()
                    self.firstLine+='%s mean,%s minimum,%s maximum,%s stddev,'%(SET,SET,SET,SET)
                    parameterList.append(str(stats.mean))
                    parameterList.append(str(stats.minimum))
                    parameterList.append(str(stats.maximum))
                    parameterList.append(str(stats.standard_deviation))

                    
                    
                    
        #check sample environment rotation stage
        angle=0.
        for SE in self.SERotOptions:            
            if ws.getRun().hasProperty(SE):
                stats=ws.getRun().getProperty(SE).getStatistics()
                angle=stats.mean
                if SE not in self.log_list:  #make sure not to write again, if it was in log_list 
                    self.log_list.append(SE) #next time is in the log_list
                    self.firstLine+='%s mean,%s minimum,%s maximum,%s stddev,'%(SE,SE,SE,SE)

                    parameterList.append(str(stats.mean))
                    parameterList.append(str(stats.minimum))
                    parameterList.append(str(stats.maximum))
                    parameterList.append(str(stats.standard_deviation))

        outstr=','.join(parameterList)

        return [outstr,angle]
        
    def save_line(self,IWSName, **kwargs):
        for key,value in kwargs.iteritems():
            if key not in self.kwds:
                self.kwds.append(key)
        
        [outstr,angle]=self.log_line_gen(IWSName)       
        
        header=self.firstLine+','.join(self.kwds)
        outstr+=','
        for k in self.kwds:
            val=kwargs.get(k,None)
            if val==None:
                outstr+='N/A,'
            else:
                outstr+=str(val)+','
                
        try:
            rhandle=open(self.Filename,'r')#see if file is there
            rhandle.close()
        except IOError:
            whandle=open(self.Filename,'w')#if not, write header
            whandle.write(header+'\n')
            whandle.close()
        
        ahandle=open(self.Filename,'a')
        ahandle.write(outstr+'\n')
        ahandle.close()
            
        return angle
    
    
def ShiftTime(WName,lg_name):
    """
    shift the time in a given log to match the time in the proton charge log"
    """
    H_IN = mantid.mtd[WName]
    PC =  H_IN.getRun()['proton_charge'].firstTime()
    P =  H_IN.getRun()[lg_name].firstTime()
    Tdiff = PC-P
    Tdiff_num = Tdiff.total_milliseconds()*1E-3
    mantid.simpleapi.ChangeLogTime(InputWorkspace=WName, OutputWorkspace = WName, LogName = lg_name, TimeOffset = Tdiff_num)
	
def CorrectLogs(WSName):
    r=mantid.mtd['__IWS'].getRun()
    for x in r.keys():
        if x not in ['duration','proton_charge','start_time','run_title','run_start','run_number','gd_prtn_chrg','end_time']:
            try:
                ShiftTime('__IWS',x)
            except:
                pass 
                
def GetEiT0(ws_name,EiGuess):
    if mean(mantid.mtd[ws_name].getRun()['vChTrans'].value) == 2:
        Ei='N/A'
        Tzero='N/A'
    else:    
        try:
            wm=mantid.mtd[ws_name]
            #fix more than 2 monitors
            sp1=0
            sp2=1
            nsp=wm.getNumberHistograms()
            if nsp < 2:
                raise ValueError("There are less than 2 monitors")
            for sp in range(nsp):
                if wm.getSpectrum(sp).getDetectorIDs()[0]==-1:
                    sp1=sp
                if wm.getSpectrum(sp).getDetectorIDs()[0]==-2:
                    sp2=sp                 
            #change frame for monitors. ARCS monitors would be in the first frame for Ei>10meV
            so=wm.getInstrument().getSource().getPos()
            m1=wm.getDetector(sp1).getPos()
            m2=wm.getDetector(sp2).getPos()
            v=437.4*sqrt(wm.getRun()['EnergyRequest'].getStatistics().mean)
            t1=m1.distance(so)*1e6/v
            t2=m2.distance(so)*1e6/v
            t1f=int(t1*60e-6)
            t2f=int(t2*60e-6)
            wm=mantid.simpleapi.ChangeBinOffset(wm,t1f*16667,0,0)
            wm=mantid.simpleapi.ChangeBinOffset(wm,t2f*16667,1,1)
            wm=mantid.simpleapi.Rebin(InputWorkspace=wm,Params="1",PreserveEvents=True)	
            alg=mantid.simpleapi.GetEi(InputWorkspace=wm,Monitor1Spec=sp1+1,Monitor2Spec=sp2+1,EnergyEstimate=float(EiGuess))				#Run GetEi algorithm
            Ei=alg[0]
            Tzero=alg[3]					#Extract incident energy and T0
        except:
            raise RuntimeError("Could not get Ei, and this is not a white beam run")
    return [Ei,Tzero]
