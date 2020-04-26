#!/usr/bin/env python

import sys,os
sys.path.append("/opt/mantidnightly/bin")
from numpy import *
from string import *

import mantid

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
        try:  # python 3
            for key,value in kwargs.items():
                if key not in self.kwds:
                    self.kwds.append(key)
        except AttributeError:  # python 2
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
    
    

