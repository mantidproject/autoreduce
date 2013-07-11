#!/usr/bin/env python
VERSION = "1.4.2"

from suds.client import Client
import sys

def createUser(sessionId, factory, service, userName):
    user = factory.create("user")
    user.name = userName 
    service.create(sessionId, user)

def createUserGroup(sessionId, factory, service, userName, groupName):
    user = service.search(sessionId, "User [name = '" + userName + "']")
    group = service.search(sessionId, "Group [name = '" + groupName + "']")

    usergroup = factory.create("userGroup")
    usergroup.user = user 
    usergroup.group = group 
    service.create(sessionId, usergroup)

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

    print 'creating user, group...'
    createUser(sessionId, factory, service, userName)
    createUserGroup(sessionId, factory, service, userName, groupName)

    service.logout(sessionId) 

if __name__ == "__main__":
   main(sys.argv[1:])
