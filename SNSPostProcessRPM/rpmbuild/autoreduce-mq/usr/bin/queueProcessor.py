#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, subprocess, psutil, time

from PostProcess import PostProcess 
from queueListener import Listener, Client,Configuration


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
        proc = subprocess.Popen(["python", "/usr/bin/PostProcess.py", destination, message])
        
        #while proc.poll() is None:
        #    print "Still working"
        #    time.sleep(1.0)

        
        
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
