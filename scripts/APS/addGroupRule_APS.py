#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client
import sys

def createGroup(sessionId, factory, service, groupName):
    group = factory.create("group")
    group.name = groupName 
    service.create(sessionId, group)

def createUserGroup(sessionId, factory, service, userName, groupName):
    user = service.search(sessionId, "User [name = '" + userName + "']")
    group = service.search(sessionId, "Group [name = '" + groupName + "']")

    usergroup = factory.create("userGroup")
    usergroup.user = user
    usergroup.group = group
    service.create(sessionId, usergroup)

def createBaseRule(sessionId, factory, service, groupName):
    group = service.search(sessionId, "Group [name = '" + groupName + "']")
    rule = factory.create("rule")
    rule.group = group
    rule.crudFlags = "R" 

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

def createRule(sessionId, factory, service, groupName):
    group = service.search(sessionId, "Group [name = '" + groupName + "']")
    rule = factory.create("rule")
    rule.group = group
    rule.crudFlags = "R"

    rule.what = "Investigation [name = 'IPTS-8072']"
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

def searchUser(sessionId, service):
    users = service.search(sessionId, "User [name in ('root')]")
    for user in users:
        print user.name

def main(argv):
    args = sys.argv[1:]
    if len(args) != 4:
        usage()

    hostAndPort = args[0]
    password = args[1]
    userName = args[2]
    groupName = args[3]

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

    print 'creating group...'
    #createGroup(sessionId, factory, service, groupName)
    createUserGroup(sessionId, factory, service, userName, groupName)

    print 'creating rules...'
    #createBaseRule(sessionId, factory, service, groupName)
    #createRule(sessionId, factory, service, groupName)

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
