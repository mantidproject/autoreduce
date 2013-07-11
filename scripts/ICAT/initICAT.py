#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client
import sys

def createUser(sessionId, factory, service):
    user = factory.create("user")
    user.name = "root"
    service.create(sessionId, user)

def createGroup(sessionId, factory, service):
    group = factory.create("group")
    group.name = "admin" 
    service.create(sessionId, group)

def createUserGroup(sessionId, factory, service):
    user = service.search(sessionId, "User [name = 'root']")
    group = service.search(sessionId, "Group [name = 'admin']")

    usergroup = factory.create("userGroup")
    usergroup.user = user 
    usergroup.group = group 
    service.create(sessionId, usergroup)

def createBaseRule(sessionId, factory, service):
    group = service.search(sessionId, "Group [name = 'admin']")
    rule = factory.create("rule")
    rule.group = group
    rule.crudFlags = "CR" 

    rule.what = "Facility"
    service.create(sessionId, rule)

    rule.what = "Instrument"
    service.create(sessionId, rule)

    rule.what = "InvestigationType"
    service.create(sessionId, rule)

    rule.what = "DatasetType"
    service.create(sessionId, rule)

    rule.what = "DatafileFormat"
    service.create(sessionId, rule)

    rule.what = "SampleType"
    service.create(sessionId, rule)

    rule.what = "ParameterType"
    service.create(sessionId, rule)

def createRule(sessionId, factory, service):
    group = service.search(sessionId, "Group [name = 'admin']")
    rule = factory.create("rule")
    rule.group = group
    rule.crudFlags = "CRUD" 
    rule.what = "Investigation <-> InvestigationParameter <-> Dataset <-> DatasetParameter <-> Sample <-> Datafile <-> DatafileParameter"
    service.create(sessionId, rule)

def createFacility(sessionId, factory, service):
    facility = factory.create("facility")
    facility.name = "SNS"
    service.create(sessionId, facility)

def createInstrument(sessionId, factory, service):
    instruments = []
    facility = service.search(sessionId, "Facility [name = 'SNS']")

    file = open("instrument.ini")
    for line in file.xreadlines():
        name, fullName, description = line.split(', ')
        instrument = factory.create("instrument")
        instrument.facility = facility
        instrument.name = name 
        instrument.fullName = fullName 
        instrument.description = description 
        instruments.append(instrument)

    service.createMany(sessionId, instruments)

def createTypes(sessionId, factory, service):
    facility = service.search(sessionId, "Facility [name = 'SNS']")

    invType = factory.create("investigationType")
    invType.name = "experiment"
    invType.facility = facility 
    service.create(sessionId, invType)

    dsType = factory.create("datasetType")
    dsType.name = "experiment_raw"
    dsType.facility = facility 
    service.create(sessionId, dsType)

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "nxs"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "dat"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "xml"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

    sampleType = factory.create("sampleType")
    sampleType.name = "default"
    sampleType.facility = facility 
    service.create(sessionId, sampleType)

def createParameterTypes(sessionId, factory, service):
    paramTypes = []
    facility = service.search(sessionId, "Facility [name = 'SNS']")

    file = open("parameter.ini")
    for line in file.xreadlines():
        name, units, valueType, applicableToInvestigation, applicableToSample = line.rstrip().split(', ')
        paramType = factory.create("parameterType")
        paramType.facility = facility
        paramType.name = name
        paramType.units = units 
        paramType.valueType = valueType
        paramType.applicableToInvestigation = applicableToInvestigation
        paramType.applicableToSample = applicableToSample
        paramTypes.append(paramType)

    service.createMany(sessionId, paramTypes)

def searchUser(sessionId, service):
    users = service.search(sessionId, "User [name in ('root')]")
    for user in users:
        print user.name

def main(argv):
    args = sys.argv[1:]
    if len(args) != 2:
        usage()

    hostAndPort = args[0]
    password = args[1]

    client = Client("https://" + hostAndPort + "/ICATService/ICAT?wsdl")
    service = client.service
    factory = client.factory

    sessionId = service.login("root", password)

    searchUser(sessionId, service)

    print 'creating user, group...'
    createUser(sessionId, factory, service)
    createGroup(sessionId, factory, service)
    createUserGroup(sessionId, factory, service)

    print 'creating rules...'
    createBaseRule(sessionId, factory, service)
    createRule(sessionId, factory, service)

    print 'creating facility, instruments...'
    createFacility(sessionId, factory, service)
    createInstrument(sessionId, factory, service)

    print 'creating type, format...'
    createTypes(sessionId, factory, service)
    createParameterTypes(sessionId, factory, service)

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
