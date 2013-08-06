#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp, subprocess, socket
from string import join
import json, sys
from PostProcess import PostProcess 
from queueListener import Listener, Client,Configuration


post_processing_bin = sys.path.append("/usr/bin") 
os.environ['NEXUSLIB'] = "/usr/lib64/libNeXus.so"

from ingestNexus_mq import IngestNexus
from ingestReduced_mq import IngestReduced


class StreamToLogger(object):
    #Fake file-like stream object that redirects writes to a logger instance.
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''
 
    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())
                                        
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
    filename='/var/log/SNS_applications/post_process.log',
    filemode='a'
)
                            
stdout_logger = logging.getLogger('STDOUT')
sl = StreamToLogger(stdout_logger, logging.INFO)
sys.stdout = sl
 
stderr_logger = logging.getLogger('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl


class PostProcessListener(Listener):
    """
    ActiveMQ listener implementation for a post process client.
    """
    ## Connection used for sending messages
    _send_connection = None
    
    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """
        
        if self._send_connection is None:
            self._send_connection = self.configuration.get_client('post_process_listener') 
        
        try:
            logging.info("message: " + message)
            data = json.loads(message)
            logging.info("data: " + str(data))
        except ValueError:   
            logging.error("Could not load JSON data: " + message)
            self._send_connection.send("/queue/POSTPROCESS.ERROR", "Could not load JSON data" + message)
            logging.info("Called /queue/POSTPROCESS.ERROR -- " + "Could not load JSON data: " + message)
            return
        
        try:
            pp = PostProcess(data, self.configuration)
        except ValueError as e:
            data["error"] = str(e)
            logging.error("JSON data is incomplete: " + json.dumps(data) )
            self._send_connection.send("/queue/POSTPROCESS.ERROR", json.dumps(data))
            logging.info("Called /queue/POSTPROCESS.ERROR -- JSON data is incomplete: " + json.dumps(data))
            return

        destination = headers["destination"]
        if destination == '/queue/REDUCTION.DATA_READY':
            pp.reduce()

        elif destination == '/queue/CATALOG.DATA_READY':
            pp.catalogRaw()

        elif destination == '/queue/REDUCTION_CATALOG.DATA_READY':
            pp.catalogReduced()


def run():
    """
    Run an instance of the Post Process ActiveMQ consumer
    """
    # Look for configuration
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd,
               conf.queues, "post_process_consumer")
    c.set_listener(PostProcessListener(conf))
    c.listen_and_wait(0.1)

if __name__ == "__main__":
    run()
