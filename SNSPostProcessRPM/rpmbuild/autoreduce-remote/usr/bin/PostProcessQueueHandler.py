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

    def __init__(self, data, conf):

        logging.info("json data: " + str(data))
        data["information"] = socket.gethostname()
        self.data = data
        self.conf = conf

        try:
            if data.has_key('data_file'):
                self.data_file = str(data['data_file'])
                logging.info("data_file: " + self.data_file)
            else:
                raise ValueError("data_file is missing")

            if data.has_key('facility'):
                self.facility = str(data['facility']).upper()
                logging.info("facility: " + self.facility)
            else: 
                raise ValueError("facility is missing")

            if data.has_key('instrument'):
                self.instrument = str(data['instrument']).upper()
                logging.info("instrument: " + self.instrument)
            else:
                raise ValueError("instrument is missing")

            if data.has_key('ipts'):
                self.proposal = str(data['ipts']).upper()
                logging.info("proposal: " + self.proposal)
            else:
                raise ValueError("ipts is missing")
                
            if data.has_key('run_number'):
                self.run_number = str(data['run_number'])
                logging.info("run_number: " + self.run_number)
            else:
                raise ValueError("run_number is missing")
            
        except ValueError as e:
            logging.error("JSON data is incomplete: " + str(e))
            raise

   
    
    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """  
        
        destination = headers["destination"]
        cmd = "/sw/fermi/autoreduction/scripts/startJob.sh " + message
        logging.info("cmd: " + cmd)
        subprocess.call(cmd, shell=False)
