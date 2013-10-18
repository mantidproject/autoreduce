#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client

import nxs, os, numpy, sys, posixpath, glob, logging
import xml.utils.iso8601, ConfigParser
from datetime import datetime

class IngestReduced():
    def __init__(self, facilityName, instrumentName, investigationName, runNumber):
        self._facilityName = facilityName
        self._instrumentName = instrumentName
        self._investigationName = investigationName
        self._runNumber = runNumber
        config = ConfigParser.RawConfigParser()
        config.read('/etc/autoreduce/icatclient.properties')
        hostAndPort = config.get('icat41', 'hostAndPort')
        password = config.get('icat41', 'password')
        plugin = "db"
    
        client = Client("https://" + hostAndPort + "/ICATService/ICAT?wsdl")
        self._service = client.service
        self._factory = client.factory
 
        credentials = self._factory.create("credentials")
        entry = self._factory.create("credentials.entry")
        entry.key = "username"
        entry.value = "root"
        credentials.entry.append(entry)
        entry = self._factory.create("credentials.entry")
        entry.key = "password"
        entry.value = password
        credentials.entry.append(entry)
    
        logging.info("Begin login at: %s" % datetime.now())
        self._sessionId = self._service.login(plugin, credentials)
        logging.info("End login at: %s" % datetime.now())
   
    def logout(self): 
        logging.info("Begin logout at: %s" % datetime.now())
        self._service.logout(self._sessionId)
        logging.info("End logout at: %s" % datetime.now())

    def execute(self):
    
        config = ConfigParser.RawConfigParser()
        config.read('/etc/autoreduce/icat4.cfg')
    
        directory = "/" + self._facilityName + "/" + self._instrumentName + "/" +  self._investigationName + "/shared/autoreduce"
        logging.info("reduction output directory: %s" % directory)
    
        #set dataset name 
        dataset = self._factory.create("dataset")
    
        dsType = self._factory.create("datasetType")
        dsType.id = config.get('DatasetType', 'reduced')
        dataset.type = dsType
        dataset.name = self._runNumber  
        dataset.location = directory
        datafiles = []
    
        pattern =  '*' + self._runNumber + '*'
        logging.info("pattern: %s" % pattern)
        for dirpath, dirnames, filenames in os.walk(directory):    
            listing = glob.glob(os.path.join(dirpath, pattern))
            for filepath in listing:
                filename =os.path.basename(filepath)
                logging.info("filename: %s" % filename)
                datafile = self._factory.create("datafile")
                datafile.location = filepath 
                datafile.name = filename
                extension = os.path.splitext(filename)[1][1:]
                dfFormat = self._factory.create("datafileFormat")
                dfFormat.id = config.get('DatafileFormat', extension)
                datafile.datafileFormat = dfFormat 
                modTime = os.path.getmtime(filepath)
                datafile.datafileCreateTime = xml.utils.iso8601.tostring(modTime)
                datafile.fileSize = os.path.getsize(filepath)
    
                datafiles.append(datafile)
    
        dataset.datafiles = datafiles
        dataset.type = dsType
        
        dbDatasets = self._service.search(self._sessionId, "Dataset INCLUDE Datafile [name = '" + str(dataset.name) + "'] <-> Investigation <-> Instrument [name = '" + str(self._instrumentName) + "'] <-> DatasetType [name = 'reduced']")

        if len(dbDatasets) == 0:
    
            dbInvestigations = self._service.search(self._sessionId, "Investigation INCLUDE Sample [name = '" + str(self._investigationName) + "'] <-> Instrument [name = '" + self._instrumentName + "'] <-> Dataset [name = '" + str(dataset.name) + "']")
        
            if len(dbInvestigations) == 1:
                investigation = dbInvestigations[0]
            else:
                logging.error("ERROR, there should be only one investigation per instrument per investigation name") 
                return 1

            logging.info("Creating dataset: %s" % datetime.now())
            dataset.investigation = investigation
            dataset.sample = investigation.samples[0]
            self._service.create(self._sessionId, dataset)
            
        elif len(dbDatasets) == 1:
    
            logging.info("reduced dataset %s is already cataloged, updating reduced dataset... " % (dataset.name))
        
            dbDataset = dbDatasets[0]
            logging.info("  dataset: %s" % str(dbDataset.id))
        
            # update "one to many" relationships
            if hasattr(dbDataset, "datafiles"):
                dfs = getattr(dbDataset, "datafiles")
                self._service.deleteMany(self._sessionId, dfs)
            
            for df in datafiles:
                 df.dataset = dbDataset
            self._service.createMany(self._sessionId, datafiles)
        
        else:
            logging.error("ERROR, there should be only one dataset per run number per type reduced")

        logging.info("DATASET:")
        logging.info("  RUN NUMBER: %s" % str(dataset.name))
        logging.info("  TITLE: %s" % str(dataset.description))
        logging.info("  START TIME: %s" % str(dataset.startDate))
        logging.info("  END TIME: %s" % str(dataset.endDate))
    
        for datafile in dataset.datafiles:
            logging.info("DATAFILE:")
            logging.info("  NAME: %s" % str(datafile.name))
            logging.info("  LOCATION: %s" %str(datafile.location))
