import json, logging, time, subprocess, sys, socket
import os

from twisted.internet import reactor, defer
from stompest import async, sync
from stompest.config import StompConfig
from stompest.async.listener import SubscriptionListener
from stompest.protocol import StompSpec, StompFailoverUri
from Configuration import Configuration


class Consumer(object):
        
    def __init__(self, config):
        self.stompConfig = StompConfig(config.uri, config.amq_user, config.amq_pwd)
        self.config = config
        self.procList = []
        
    @defer.inlineCallbacks
    def run(self):
        self.heartbeat()
        client = yield async.Stomp(self.stompConfig).connect()
        headers = {
            # client-individual mode is necessary for concurrent processing
            # (requires ActiveMQ >= 5.2)
            StompSpec.ACK_HEADER: StompSpec.ACK_CLIENT_INDIVIDUAL,
            # the maximal number of messages the broker will let you work on at the same time
            'activemq.prefetchSize': '1',
        }

        for q in self.config.queues:
            client.subscribe(q, headers, listener=SubscriptionListener(self.consume, errorDestination=self.config.postprocess_error))
            
        try:
            client = yield client.disconnected
        except:
            reactor.callLater(5, self.run)
            logging.info("callLater in 5 seconds")
            
    def consume(self, client, frame):
        """
        NOTE: you can return a Deferred here
        """
        headers = frame.headers
        destination = headers['destination']
        data = frame.body

        logging.info("Received frame destination: " + destination)
        logging.info("Received frame body (data): " + data) 
        cmd = self.config.sw_dir + "/startJob.sh"
        logging.info("Command: " + cmd) 
        data = "'" + data.replace(" ", "") + "'"
        proc = subprocess.Popen([cmd, data])
        self.procList.append(proc)

        while len(self.procList) > 4:
            logging.info("There are " + str(len(self.procList)) + " processors running at the moment, wait for a second")
            time.sleep(1.0)
            self.updateChildProcessList()

        self.updateChildProcessList()
        
    def updateChildProcessList(self):
        for i in self.procList:
            if i.poll() is not None:
                self.procList.remove(i)
                
    def heartbeat(self):
        """
            Send heartbeats at a regular time interval
        """
        logging.info("In heartbeat...")
        try:
            stomp = sync.Stomp(self.stompConfig)
            stomp.connect()
            data_dict = {"src_name": socket.gethostname(), "status": "0", "pid": str(os.getpid())}
            stomp.send(self.config.heart_beat, json.dumps(data_dict))
            logging.info("called " + self.config.heart_beat + " --- " + json.dumps(data_dict))
            stomp.disconnect()
        except:
            logging.error("Could not send heartbeat: %s" % sys.exc_value)
        reactor.callLater(30.0, self.heartbeat)
 
if __name__ == '__main__':

    try:
        config = Configuration('/etc/autoreduce/post_process_consumer.conf')
    except:
        sys.exit()
        
    logging.info("Start post process asynchronous listener!")
    Consumer(config).run()
    reactor.run()
    logging.info("Stop post process asynchronous listener!")
