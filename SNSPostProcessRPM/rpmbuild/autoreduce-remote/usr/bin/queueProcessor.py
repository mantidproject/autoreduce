#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp, subprocess
from string import join
from queueListener import Client, Configuration, Listener

from MantidFramework import mtd
import mantid.simpleapi as api
mtd.initialize()
from mantidsimple import *


post_processing_bin = sys.path.append("/usr/bin") 

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
        try:
            destination = headers["destination"]
            logging.info("destination=" + destination)
            logging.info("message=" + message)
            data = json.loads(message)
            
            if data.has_key('data_file'):
                path = str(data['data_file'])
                logging.info("path = " + path)
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
                
            if data.has_key('run_number'):
                run_number = str(data['run_number'])
                logging.info("run_number: "+run_number)
            else: 
                data["error"] = "run_number is missing"      

            if data.has_key('error'):
                logging.info("Calling /queue/"+self.configuration.catalog_error_queue+json.dumps(data)) 
                self._send_connection.send('/queue/'+self.configuration.catalog_error_queue, json.dumps(data))
                return
                
            logging.info("Calling /queue/"+self.configuration.reduction_started_queue+message)             
            self._send_connection.send('/queue/'+self.configuration.reduction_started_queue, message)
            
            root_dir = self.configuration.root_dir
            
            out_dir = self.configuration.log_dir + "/reduction_log/"
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
                
            err_dir = self.configuration.log_dir
            logging.info("input file: " + path + ", out directory: " + out_dir)
            
            #MaxChunkSize is set to 32G specifically for the jobs run on fermi, which has 32 nodes and 64GB/node
            #We would like to get MaxChunkSize from an env variable in the future
            
            Chunks = api.DetermineChunking(Filename=path,MaxChunkSize=32.0)
            nodesDesired = Chunks.rowCount()
            logging.info("nodesDesired: " + str(nodesDesired))
            if nodesDesired > 32:
                nodesDesired = 32
                
            cmd = "qsub -v data_file='" + path + "',facility='" + facility + "',instrument='" + instrument + "',out_dir='" + out_dir + "' -l nodes=" + str(nodesDesired) + ":ppn=1 " + root_dir + "/startMPIRun.sh"
            logging.info("cmd: " + cmd)
            out_log = os.path.join(out_dir, instrument + "_" + run_number + ".log")
            out_err = os.path.join(err_dir, instrument + "_" + run_number + ".err")
            logFile=open(out_log, "w")
            errFile=open(out_err, "w")
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=logFile, stderr=errFile, universal_newlines = True)
            proc.communicate()
            logFile.close()
            errFile.close()
            logging.info("Calling /queue/"+self.configuration.reduction_complete_queue+message)             
            self._send_connection.send('/queue/'+self.configuration.reduction_complete_queue, message)
        except Exception, e:
            data["error"] = "REDUCTION: %s " % e 
            logging.error("Calling /queue/"+self.configuration.reduction_error_queue + json.dumps(data))
            self._send_connection.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))
            
        logging.info("Done with reduction on fermi")


def run():
    """
    Run an instance of the Post Process ActiveMQ consumer
    """
    # Look for configuration
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd,
               conf.root_dir, conf.log_dir, conf.queues,  "post_process_consumer")
    c.set_listener(PostProcessListener(conf))
    c.listen_and_wait(0.1)

if __name__ == "__main__":
    run()
