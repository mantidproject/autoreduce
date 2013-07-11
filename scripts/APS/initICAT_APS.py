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

    rule.what = "Investigation"
    service.create(sessionId, rule)

    rule.what = "Dataset"
    service.create(sessionId, rule)

    rule.what = "DatasetParameter"
    service.create(sessionId, rule)

    rule.what = "Sample"
    service.create(sessionId, rule)

    rule.what = "SampleParameter"
    service.create(sessionId, rule)

    rule.what = "Datafile"
    service.create(sessionId, rule)

    rule.what = "DatafileParameter"
    service.create(sessionId, rule)

def createFacility(sessionId, factory, service):
    facility = factory.create("facility")
    facility.name = "APS"
    service.create(sessionId, facility)

def createInstrument(sessionId, factory, service):
    instruments = []
    facility = service.search(sessionId, "Facility [name = 'APS']")
    instrument = factory.create("instrument")
    instrument.facility = facility
    instrument.name = '11-ID-B' 
    instrument.fullName = '11-ID-B' 
    instruments.append(instrument)
    service.createMany(sessionId, instruments)

def createTypes(sessionId, factory, service):
    facility = service.search(sessionId, "Facility [name = 'APS']")

    invType = factory.create("investigationType")
    invType.name = "experiment"
    invType.facility = facility 
    service.create(sessionId, invType)

    dsType = factory.create("datasetType")
    dsType.name = "experiment_raw"
    dsType.facility = facility 
    service.create(sessionId, dsType)

    dsType = factory.create("datasetType")
    dsType.name = "reduced"
    dsType.facility = facility 
    service.create(sessionId, dsType)

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "tif"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "chi"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

def createParameterTypes(sessionId, factory, service):
    paramTypes = []
    facility = service.search(sessionId, "Facility [name = 'APS']")

    file = open("parameter_aps.ini")
    for line in file.xreadlines():
        name, units, valueType, applicableToDataFile = line.rstrip().split(', ')
        paramType = factory.create("parameterType")
        paramType.facility = facility
        paramType.name = name
        paramType.units = units 
        paramType.valueType = valueType
        paramType.applicableToDatafile = 1 
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

    sessionId = service.login(plugin, credentials)

    #searchUser(sessionId, service)
    print 'creating user, group...'
    '''createUser(sessionId, factory, service)
    createGroup(sessionId, factory, service)
    createUserGroup(sessionId, factory, service)'''

    print 'creating rules...'
    createBaseRule(sessionId, factory, service)
    #createRule(sessionId, factory, service)

    print 'creating facility, instruments...'
    '''createFacility(sessionId, factory, service)
    createInstrument(sessionId, factory, service)

    print 'creating type, format...'
    createTypes(sessionId, factory, service)
    createParameterTypes(sessionId, factory, service)'''

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
