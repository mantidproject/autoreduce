#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client
from datetime import datetime
import sys

def createTypes(sessionId, factory, service):
    facility = service.search(sessionId, "Facility [name = 'SNS']")
    dsType = factory.create("datasetType")
    dsType.name = "simulation"
    dsType.facility = facility 
    service.create(sessionId, dsType)

    dsFormat1 = factory.create("datafileFormat")
    dsFormat1.name = "in"
    dsFormat1.facility = facility 
    service.create(sessionId, dsFormat1)

    dsFormat2 = factory.create("datafileFormat")
    dsFormat2.name = "out"
    dsFormat2.facility = facility 
    service.create(sessionId, dsFormat2)

    dsFormat = factory.create("datafileFormat")
    dsFormat.name = "unknown"
    dsFormat.facility = facility 
    service.create(sessionId, dsFormat)

def createApplication(sessionId, factory, service):
    app = factory.create("application")
    app.name = "kepler-dakota"
    app.version = "1.0"
    service.create(sessionId, app)


def createParameterTypes(sessionId, factory, service):
    paramTypes = []
    facility = service.search(sessionId, "Facility [name = 'SNS']")

    file = open("parameter_camm.ini")
    for line in file.xreadlines(): 
        name, units, valueType = line.rstrip().split(', ')
        paramType = factory.create("parameterType")
        paramType.facility = facility
        paramType.name = name
        paramType.units = units
        paramType.valueType = valueType
        paramType.applicableToDatafile = 1 
        paramTypes.append(paramType)

    service.createMany(sessionId, paramTypes)


def main(argv):
    args = sys.argv[1:]
    if len(args) != 2:
        usage()

    hostAndPort = args[0]
    password = args[1]
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

    print 'creating type, format...'
    #createTypes(sessionId, factory, service)

    print 'creating application'
    #createApplication(sessionId, factory, service)

    print 'creating parameter type'
    createParameterTypes(sessionId, factory, service)

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
