#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp, subprocess, socket
from string import join
import json, sys

from PostProcess import PostProcess 
from queueListener import Listener, Client,Configuration

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
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
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

        destination = headers["destination"]
        subprocess.Popen(["python", "/usr/bin/PostProcess.py", destination, message])
        
        
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
