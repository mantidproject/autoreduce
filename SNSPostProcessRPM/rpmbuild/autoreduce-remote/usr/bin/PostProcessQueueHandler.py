#!/usr/bin/env python
"""
Post Process Queue Handler. It dispatches job based on numbers of cores on the machine
"""
import subprocess, time, logging
from Listener import Listener


class PostProcessQueueHandler(Listener):
    """
    ActiveMQ listener implementation for a post process client.
    """
    ## Connection used for sending messages

    def __init__(self):
        self._proc_list = []
   
    
    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """

        destination = headers["destination"]
        logging.info("message: " + message)
        proc = subprocess.Popen(["python", "/usr/bin/PostProcessAdmin.py", destination, message])
        self._proc_list.append(proc)
                          
        while len(self._proc_list) > 4:
            logging.info("There are " + str(len(self._proc_list)) + " processors running at the moment, wait for a second")
            time.sleep(1.0)
            self.updateChildProcessList()
                          
        self.updateChildProcessList()
            
    def updateChildProcessList(self):
        for i in self._proc_list:
            if i.poll() is not None:
                self._proc_list.remove(i)