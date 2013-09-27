#!/usr/bin/python
from suds.client import Client

import nxs, os, numpy, sys, posixpath, glob
import xml.utils.iso8601, ConfigParser
from datetime import datetime

def Uage():
  print 'Usage: python ingestDakota.py <jobId> <inputFileDirectory> <outputFileDirectory>'
  print 'Example: python ingestDakota.py 872.fermi-mgmt3.ornl.gov /tmp/data/Dakota_input /tmp/data/Dakota_output'
  sys.exit(-1)

def getSimulationData(dsName, sessionId, service, factory):
  config = ConfigParser.RawConfigParser()
  config.read('camm.cfg')

  dbDatasets = service.search(sessionId, "Dataset INCLUDE Datafile, DatafileParameter, ParameterType [name = '" + str(dsName) + "'] <-> DatasetType [name = 'simulation']")

  if len(dbDatasets) == 0:
    
    print "Dataset %s is not found" %(dsName)
            
  elif len(dbDatasets) == 1:
    dbDataset = dbDatasets[0]
    print "  dataset name: %s"%(str(dbDataset.name))
        
    # update "one to many" relationships
  
    if hasattr(dbDataset, "datafiles"):
      dfs = getattr(dbDataset, "datafiles")
            
      inputFiles = []
      assembledOutputFiles = []
      convolvedOutputFiles = []
      resultOutputFiles = []
      for df in dfs:
        if str(df.description) == "input":
          inputFiles.append(df.location)
          #print "%s file: %s"%(str(df.description), str(df.location))
        else:
          if "assembled" in df.name:
            assembledOutputFiles.append(df)
          elif "convolved" in df.name:
            convolvedOutputFiles.append(str(df.location))
          elif "result" in df.name:
            resultOutputFiles.append(str(df.location))
          else:
            "Unknown imulation output files"
        
      inputFiles.sort()
      assembledOutputFiles.sort()
      convolvedOutputFiles.sort()
      resultOutputFiles.sort()
      
      print "\nparams input files:"
      for file in inputFiles:
        print file
      
      print "\nassembled output files:"
      for df in assembledOutputFiles:
        print "%s"%("\n"+str(df.location))
        for param in df.parameters:
          print "%s=%s;" %(param.type.name, param.numericValue)

      print "\nconvolved output files:"
      for file in convolvedOutputFiles:
        print file
      
      print "\nresults output files:"
      for file in resultOutputFiles:
        print file
      '''for df in dfs:
        if str(df.description) == "output":
          if "assembled" in df.name:
            for param in df.parameters:
              print param.type.name, param.numericValue
            print "%s file: %s"%(str(df.description), str(df.location))'''
            
  else:
    print "ERROR, there should be only one dataset per run number per type experiment_raw" 
        
 
def main(argv):
  args = sys.argv[1:]
  if len(args) != 1:
    usage()

  dsName = args[0]

  config = ConfigParser.RawConfigParser()
  config.read('/etc/autoreduce/icatclient.properties')
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

  print "Begin getSimulationData at: ", str(datetime.now())
  status = getSimulationData(dsName, sessionId, service, factory)
  print "End gettSimulationData at: ", str(datetime.now())

  print "Begin logout at: ", str(datetime.now())
  service.logout(sessionId)
  print "End logout at: ", str(datetime.now())

if __name__ == "__main__":
  main(sys.argv[1:])

