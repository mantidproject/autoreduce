#!/usr/bin/python
from suds.client import Client

import nxs, os, numpy, sys, posixpath, glob
import xml.utils.iso8601, ConfigParser
from datetime import datetime
from nxs import NeXusError

def usage():
  print 'Usage: python ingestDakota.py <jobId> <inputFileDirectory> <outputFileDirectory>'
  print 'Example: python ingestDakota.py 872.fermi-mgmt3.ornl.gov /tmp/data/Dakota_input /tmp/data/Dakota_output'
  sys.exit(-1)

def ingestSimulationData(datafileDir, sessionId, service, factory):
  print "datafileDir: %s" %datafileDir
  config = ConfigParser.RawConfigParser()
  config.read('camm.cfg')
  # get application
  appId = config.get('Application', 'kepler-dakota')
  application = factory.create("application")
  application.id = appId 

  #create job
  job = factory.create("job")
  job.application = application 
  jobId = service.create(sessionId, job)

  job.id = jobId

  #create investigation 
  facility = factory.create("facility")
  facility.id = config.get('Facility', 'sns')
       
  invType = factory.create("investigationType")
  invType.id = config.get('InvestigationType', 'experiment')

  investigation = factory.create("investigation")
  investigation.facility = facility
  investigation.type = invType 
  investigation.name = "Simulation of LiCl -- test1" 
  investigation.title = "Simulation of LiCl"  

  #create sample
  sample = factory.create("sample")
  sample.name = "LiCl"

  #create new dataset
  dsTypeId = config.get('DatasetType', 'simulation')
  dsType = factory.create("datasetType")
  dsType.id = dsTypeId 

  dataset = factory.create("dataset")
  dataset.type = dsType
  dataset.name = "test1" 
  datafiles = []
  
  paramTypes = ['FF1', 'b0', 'b1', 'c0', 'chisq','e0.0', 'e0.1', 'e0.2', 'eshift', 'norm_chi', 'norm_chisq']
    
  for dirpath, dirnames, filenames in os.walk(datafileDir):
    listing = glob.glob(os.path.join(dirpath, "*"))
    for filepath in listing:
      parameters = []
      addFile = True
      filename =os.path.basename(filepath)
      if "params.in" in filename:
        description = "input"
        name = filename.split(".")
        if len(name) == 3:
           extension = name[1]
        else:
          extension = "unknown"
      else: 
        description = "output"  
        if "assembled" in filename:
          extension = os.path.splitext(filename)[1][1:]
          file = nxs.open(filepath, 'r')
          for param in paramTypes:
            file.openpath('/mantid_workspace_1/logs/'+param+'/value')
            parameterType = factory.create("parameterType")
            parameterType.id = config.get('ParameterType', param)
            parameterType.applicableToDatafile = 1
            datafileParameter = factory.create("datafileParameter")
            datafileParameter.type = parameterType 
            datafileParameter.numericValue = file.getdata()
            parameters.append(datafileParameter)
          file.close()
        elif "convolved" in filename: 
          extension = os.path.splitext(filename)[1][1:]
        elif "results.out" in filename:
          name = filename.split(".")
          if len(name) == 3:
            extension = name[1]
          else:
            extension = "unknown"
        else:
          addFile = False
      
      if addFile == True:
        datafile = factory.create("datafile")
        datafile.location = filepath
        datafile.name = filename
        datafile.description = description
        
        dfFormat = factory.create("datafileFormat")
        dfFormat.id = config.get('DatafileFormat', extension)
        datafile.datafileFormat = dfFormat
      
        modTime = os.path.getmtime(filepath)
        datafile.datafileCreateTime = xml.utils.iso8601.tostring(modTime)
        datafile.fileSize = os.path.getsize(filepath)
        if len(parameters) != 0:
          datafile.parameters = parameters
          
        datafiles.append(datafile)
      
  dataset.datafiles = datafiles
  dataset.type = dsType
  
  dbDatasets = service.search(sessionId, "Dataset INCLUDE Datafile [name = '" + str(dataset.name) + "'] <-> Investigation [name = '" + str(investigation.name)  + "'] <-> DatasetType [name = 'simulation']")

  if len(dbDatasets) == 0:
    
    dbInvestigations = service.search(sessionId, "Investigation INCLUDE Sample [name = '" + str(investigation.name) + "']")
        
    if len(dbInvestigations) == 0: 
      print "New IPTS: creating investigation, sample, run..."
      # create new investigation
      invId = service.create(sessionId, investigation)
      investigation.id = invId
      print "  invId: %s"%(str(invId))
            
      # create new sample
      sample.investigation = investigation
      sampleId = service.create(sessionId, sample)
      sample.id = sampleId
      print "  sampleId: %s"%(str(sampleId))
        
    elif len(dbInvestigations) == 1:
      investigation = dbInvestigations[0]
      dbSamples = investigation.samples
            
      newSample = True
      for dbSample in dbSamples:
        if dbSample.name == sample.name:
          sample.id = dbSample.id
          newSample = False
            
      if newSample == True:
        print "New run: existing investigation, creating sample and run..."
        sample.investigation = investigation
        sampleId = service.create(sessionId, sample)
        sample.id = sampleId
      else:
        print "New run: existing investigation and sample, creating run..."
            
    else:
      print "ERROR, there should be only one investigation per instrument per investigation name per visit"  

    # create new dataset
    dataset.sample = sample
    dataset.investigation = investigation
    datasetId = service.create(sessionId, dataset)
    dataset.id = datasetId
    print "  datasetId: %s"%(str(datasetId))
    
    inputDS = factory.create("inputDataset")
    inputDS.job = job
    inputDS.dataset = dataset
    inputDSId = service.create(sessionId, inputDS)
            
  elif len(dbDatasets) == 1:
    print "Run %s is already cataloged, updating catalog..."%(dataset.name)
        
    dbDataset = dbDatasets[0]
    print "  datasetId: %s"%(str(dbDataset.id))
        
    # update "one to many" relationships
  
    if hasattr(dbDataset, "datafiles"):
      dfs = getattr(dbDataset, "datafiles")
      service.deleteMany(sessionId, dfs)
            
    for df in datafiles:
      df.dataset = dbDataset
      
    service.createMany(sessionId, datafiles)
        
    # update "many to one" relationships
        
    ds = service.get(sessionId, "Dataset INCLUDE 1", dbDataset.id)
    print "  ds: %s"%(str(ds))
        
    investigation.id = ds.investigation.id
        
    dbSamples = service.search(sessionId, "Sample <-> Investigation [id = '" + str(ds.investigation.id) + "']")
    updateSample = True
    for sa in dbSamples:
      if sa.name == sample.name:
        sample = sa
        updateSample = False
        print "  sample: %s"%(str(sample))
             
    if updateSample == True:
      sample.id = ds.sample.id
      sample.investigation = investigation
      service.update(sessionId, sample)
        
    dataset.id = ds.id
    dataset.sample = sample
    dataset.investigation = investigation   
        
    service.update(sessionId, dataset)
    service.update(sessionId, investigation)

  else:
    print "ERROR, there should be only one dataset per run number per type experiment_raw" 
        
 
def main(argv):
  args = sys.argv[1:]
  if len(args) != 1:
    usage()

  datafileDir = args[0]

  config = ConfigParser.RawConfigParser()
  config.read('icatclient.properties')
  hostAndPort = config.get('icat41', 'hostAndPort')
  password = config.get('icat41', 'password')
  plugin = "db"
  client = Client("https://" + hostAndPort + "/ICATService/ICAT?wsdl")
  service = client.service
  factory = client.factory
    
  credentials = factory.create("credentials")
  entry = factory.create("credentials.entry")
  entry.key = "username"
  entry.value = "root"
  credentials.entry.append(entry)
  entry = factory.create("credentials.entry")
  entry.key = "password"
  entry.value = password
  credentials.entry.append(entry)

  print "Begin login at: ", str(datetime.now())
  sessionId = service.login(plugin, credentials)
  print "End login at: ", str(datetime.now())

  print "Begin ingestSimulationData at: ", str(datetime.now())
  status = ingestSimulationData(datafileDir, sessionId, service, factory)
  print "End ingestSimulatinData at: ", str(datetime.now())

  print "Begin logout at: ", str(datetime.now())
  service.logout(sessionId)
  print "End logout at: ", str(datetime.now())

if __name__ == "__main__":
  main(sys.argv[1:])

