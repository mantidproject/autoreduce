#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client
from datetime import datetime
import sys

def createTypes(sessionId, factory, service):
    facility = service.search(sessionId, "Facility [name = 'SNS']")

    dfFormat = factory.create("datafileFormat")
    dfFormat.name = "log"
    dfFormat.facility = facility 
    service.create(sessionId, dfFormat)

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
    createTypes(sessionId, factory, service)

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
