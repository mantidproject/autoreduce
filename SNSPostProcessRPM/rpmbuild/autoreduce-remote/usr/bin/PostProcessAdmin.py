#!/usr/bin/env python
"""
PostProcessAdmin of autoreduce-remote executes reduction jobs on fermi
"""
import logging, json, socket, os, sys, subprocess

from Configuration import Configuration
from stompest.config import StompConfig
from stompest.sync import Stomp

import mantid.simpleapi as api

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
    
class PostProcessAdmin:
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

    def reduce(self):
        try:         
            self.send('/queue/'+self.conf.reduction_started, json.dumps(self.data))  
            logging.info("called /queue/" + self.conf.reduction_started + " --- " + json.dumps(self.data))  
            #proposal_shared_dir = "/" + self.facility + "/" + self.instrument + "/" + self.proposal + "/shared/autoreduce/"
            proposal_shared_dir = "/tmp/work/3qr/autoreduce/"
            log_dir = proposal_shared_dir + "reduction_log/"

            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            sw_dir = '/sw/fermi/autoreduce/scripts' 
            
            #MaxChunkSize is set to 32G specifically for the jobs run on fermi, which has 32 nodes and 64GB/node
            #We would like to get MaxChunkSize from an env variable in the future
            
            Chunks = api.DetermineChunking(Filename=data_file,MaxChunkSize=32.0)
            nodesDesired = Chunks.rowCount()
            logging.info("nodesDesired: " + str(nodesDesired))
            
            if nodesDesired > 32:
                nodesDesired = 32
                 
            cmd = "qsub -v data_file='" + self.data_file + "',facility='" + self.facility + "',instrument='" + self.instrument + "',out_dir='" + self.out_dir + "' -l nodes=" + str(nodesDesired) + ":ppn=1 " + sw_dir + "/remoteJob.sh"
            logging.info("cmd: " + cmd)
            out_log = os.path.join(out_dir, instrument + "_" + run_number + ".log")
            out_err = os.path.join(proposal_shared_dir, instrument + "_" + run_number + ".err")
        
            logFile=open(out_log, "w")
            errFile=open(out_err, "w")
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=logFile, stderr=errFile, universal_newlines = True)
            proc.communicate()
            logFile.close()
            errFile.close()

            if os.stat(out_err).st_size == 0:
                os.remove(out_err)
                self.send('/queue/'+self.conf.reduction_complete , json.dumps(self.data))  
                logging.info("called /queue/"+self.conf.reduction_complete + " --- " + json.dumps(self.data))     
            else:
                maxLineLength=80
                fp=file(out_err, "r")
                fp.seek(-maxLineLength-1, 2) # 2 means "from the end of the file"
                lastLine = fp.readlines()[-1]
                errMsg = lastLine.strip() + ", see reduction_log/" + os.path.basename(out_log) + " or " + os.path.basename(out_err) + " for details."
                self.data["error"] = "REDUCTION: %s" % errMsg
                self.send('/queue/'+self.conf.reduction_error , json.dumps(self.data))
                logging.error("called /queue/"+self.conf.reduction_error  + " --- " + json.dumps(self.data))       

        except Exception, e:
            self.data["error"] = "REDUCTION Error: %s " % e
            logging.error("called /queue/"+self.conf.reduction_error  + " --- " + json.dumps(self.data))
            self.send('/queue/'+self.conf.reduction_error , json.dumps(self.data))
            

    def send(self, destination, data):
        ppQConnector = PostProcessQueueConnector(self.conf.brokers, self.conf.amq_user, self.conf.amq_pwd, self.conf.queues, "post_process_consumer")
        ppQConnector.send(destination, json.dumps(self.data))
        
    
    def getData(self):
        return self.data
    
    
if __name__ == "__main__":
    try:
        message = sys.argv[1]
        logging.info("message: " + message)
        data = json.loads(message)
        logging.info("data: " + str(data))
    except ValueError as e:
        data["error"] = str(e)
        logging.error("JSON data is incomplete: " + json.dumps(data) )
        stomp = sync.Stomp(self.stompConfig)
        stomp.connect()
        stomp.send(self.config.heart_beat, json.dumps(data))
        stomp.disconnect() 
        logging.info("Called " + self.config.postprocess_error " + json.dumps(data))

    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
        
    pp = PostProcessAdmin(data, conf)
    pp.reduce()
        
    sys.exit()
