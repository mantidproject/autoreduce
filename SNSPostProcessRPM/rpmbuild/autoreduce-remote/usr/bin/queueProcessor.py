#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp, subprocess
from string import join
from queueListener import Client, Configuration, Listener


post_processing_bin = sys.path.append("/sw/fermi/autoreduction") 

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
    filename="/var/log/SNS_applications/post_process.log",
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
            
        # Decode the incoming message
        logging.info("destination=" + headers['destination'])
        #if headers['destination']=='/queue/'+self.configuration.ready_queue:
        if headers['destination']=='/queue/FERMI_REDUCTION.DATA_READY':
            logging.info("destination=" + headers['destination'])
            logging.info("message=" + message)
            data = json.loads(message)

            if data.has_key('data_file'):
                data_file = str(data['data_file'])
                logging.info("data_file = " + data_file)
            else: 
                data["error"] = "data_file is missing"

            if data.has_key('facility'):
                facility = str(data['facility']).upper()
                logging.info("facility: "+facility)
            else: 
                data["error"] = "facility is missing"
                        
            if data.has_key('instrument'):
                instrument = str(data['instrument']).upper()
                logging.info("instrument: "+instrument)
            else: 
                data["error"] = "instrument is missing"
                
            if data.has_key('ipts'):
                proposal = str(data['ipts']).upper()
                logging.info("proposal: "+proposal)
            else: 
                data["error"] = "instrument is missing"
                        
            if data.has_key('run_number'):
                run_number = str(data['run_number'])
                logging.info("run_number: "+run_number)
            else: 
                data["error"] = "run_number is missing"      

            if data.has_key('error'):
                logging.info("Calling /queue/"+self.configuration.reduction_error_queue+json.dumps(data)) 
                c.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))
                return
                        
            cmd = "/sw/fermi/autoreduction/scripts/startJob.sh " + facility + " " + instrument + " " + proposal + " " + run_number + " " + data_file + " "
            logging.info("cmd: " + cmd)
            subprocess.call(cmd, shell=True)

            
def run():
    """
    Run an instance of the Post Process ActiveMQ consumer
    """
    # Look for configuration
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd,
               conf.queues,  "post_process_consumer")
    c.set_listener(PostProcessListener(conf))
    c.listen_and_wait(0.1)

if __name__ == "__main__":
    run()
