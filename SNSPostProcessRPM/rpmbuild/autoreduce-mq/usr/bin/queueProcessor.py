#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, subprocess, psutil, time, logging

from PostProcess import PostProcess 
from queueListener import Listener, Client,Configuration

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
    format="%(asctime)s %(levelname)s %(name)s %(process)d/%(threadName)s: %(message)s",
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

    def __init__(self, conf):
        self.proc_list = []
        self._send_connection = None
        self.conf = conf
        
    
    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """
        
        if self._send_connection is None:
            self._send_connection = self.conf.get_client('post_process_listener') 

        destination = headers["destination"]
        proc = subprocess.Popen(["python", "/usr/bin/PostProcess.py", destination, message])
        self.proc_list.append(proc)
        
                
        while len(self.proc_list) > 4:
            for i in self.proc_list:
                if i.poll() is not None:
                    self.proc_list.remove(i)
            logging.info("Still working: " + str(len(self.proc_list)))
            time.sleep(1.0)

        

if __name__ == "__main__":
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    ppListener = PostProcessListener(conf)
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd, conf.queues, "post_process_consumer")
    c.set_listener(ppListener)
    c.listen_and_wait(0.1)