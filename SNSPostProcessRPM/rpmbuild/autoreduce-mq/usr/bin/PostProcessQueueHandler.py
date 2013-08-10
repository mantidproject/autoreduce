#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, subprocess, psutil, time, logging, stomp
from Listener import Listener


class PostProcessQueueHandler(Listener):
    """
    ActiveMQ listener implementation for a post process client.
    """
    ## Connection used for sending messages

    def __init__(self, conf):
        self._proc_list = []
        self._send_connection = None
        self._conf = conf
        
    
    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """
        
        if self._send_connection is None:
            self._send_connection = self._conf.get_client('post_process_consumer') 

        destination = headers["destination"]
        proc = subprocess.Popen(["python", "/usr/bin/PostProcessAdmin.py", destination, message])
        self._proc_list.append(proc)
        
                
        while len(self._proc_list) > 4:
            logging.info("Still working: " + str(len(self._proc_list)))
            time.sleep(1.0)
            for i in self._proc_list:
                if i.poll() is not None:
                    self._proc_list.remove(i)
