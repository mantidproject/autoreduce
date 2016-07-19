import json, time, subprocess, sys
import stomp
from twisted.internet import reactor
from autoreduction_logging_setup import logger

class Listener(object):
    def __init__(self, client):
        self._client = client
        self.procList = []
        self.RBList = [] # list of RB numbers of active reduction runs
        self.max_subprocesses = 5  # processes allowed to run at one time

    def on_error(self, headers, message):
        logger.error("Error message recieved - %s" % str(message))

    def on_message(self, headers, data):
        try:
            self._client.ack(headers['message-id'], headers['subscription'])  # Remove message from queue

            destination = headers['destination']

            logger.debug("Received frame destination: " + destination)
            logger.debug("Recieved frame priority: " + headers["priority"])
            logger.debug("DATA: %s" % data)

            data_dict = json.loads(data)

            while not self.shouldProceed(data_dict): # wait while the run shouldn't proceed
                logger.debug("waiting")
                self.updateChildProcessList()
                time.sleep(10.0)

            logger.debug("Calling: %s %s %s %s" % ("python", "/usr/bin/PostProcessAdmin.py", destination, data))
            proc = subprocess.Popen(["python", "/usr/bin/PostProcessAdmin.py", destination, data])
            self.addProc(proc, data_dict)

        except e:
            logger.info("Exception in queueProcessor message handling: %s - %s" % (type(e).__name__, e))
        
        
    def updateChildProcessList(self):
        for i in self.procList:
            if i.poll() is not None:
                index = self.procList.index(i)
                del self.procList[i]
                del self.RBList[i]
                
    def addProc(self, proc, data_dict):
        self.procList.append(proc)
        self.RBList.append(data_dict["rb_number"])
        
    def shouldProceed(self, data_dict):
        if data_dict["rb_number"] in self.RBList:
            logger.info("Duplicate RB run #" + data_dict["rb_number"] + ", waiting for the first to finish.")
            return False
            
        # elif len(self.procList) >= process_num:
            # logger.info("There are " + str(len(self.procList)) + " processes running at the moment, max is " + self.max_subprocesses "+ . Waiting until one is available.")
            # return False
            
        else:
            logger.debug("proceeding")
            return True


class Consumer(object):
        
    def __init__(self, config):
        self.config = config
        self.consumer_name = "queueProcessor"
        
    def run(self):
        brokers = [(self.config['brokers'].split(':')[0],int(self.config['brokers'].split(':')[1]))]
        connection = stomp.Connection(host_and_ports=brokers, use_ssl=False, ssl_version=3)
        connection.set_listener(self.consumer_name, Listener(connection))
        connection.start()
        connection.connect(self.config['amq_user'], self.config['amq_pwd'], wait=False, header={'activemq.prefetchSize': '1'})
        
        for queue in self.config['amq_queues']:
            connection.subscribe(destination=queue, id=1, ack='client-individual', header={'activemq.prefetchSize': '1'})
            logger.info("[%s] Subscribing to %s" % (self.consumer_name, queue))

def main():
    try:
        config = json.load(open('/etc/autoreduce/post_process_consumer.conf'))
    except:
        logger.info("Can't open post_process_consumer.conf")
        sys.exit()
        
    logger.info("Start post process asynchronous listener!")
    reactor.callWhenRunning(Consumer(config).run)
    reactor.run()
    logger.info("Stop post process asynchronous listener!")

if __name__ == '__main__':
    main()
