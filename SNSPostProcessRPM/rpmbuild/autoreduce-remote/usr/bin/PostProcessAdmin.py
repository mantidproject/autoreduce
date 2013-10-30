#!/usr/bin/env python
"""
PostProcessAdmin of autoreduce-remote executes reduction jobs on fermi
"""
import logging, json, socket, os, sys, subprocess, time

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
    filename="/lustre/snsfs/logs/SNS_applications/post_process.log",
    #filename="/tmp/work/3qr/post_process.log",
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
        self.sw_dir = conf.sw_dir

        stompConfig = StompConfig(self.conf.brokers, self.conf.amq_user, self.conf.amq_pwd)
        self.client = Stomp(stompConfig)
        
        try:
            if data.has_key('data_file'):
                self.data_file = str(data['data_file'])
                logging.info("data_file: " + self.data_file)
                if os.access(self.data_file, os.R_OK) == False:
                    raise ValueError("data_file path doesn't exist or file not readable")
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
            logging.info('JSON data error', exc_info=True)
            raise

    def reduce(self):
        try:         
            self.send('/queue/'+self.conf.reduction_started, json.dumps(self.data))  
            logging.info("called /queue/" + self.conf.reduction_started + " --- " + json.dumps(self.data))  
            proposal_shared_dir = "/" + self.facility + "/" + self.instrument + "/" + self.proposal + "/shared/autoreduce/"
            #proposal_shared_dir = "/tmp/work/3qr/"
            log_dir = proposal_shared_dir + "reduction_log/"

            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
        
            out_log = os.path.join(log_dir, os.path.basename(self.data_file) + ".log")
            out_err = os.path.join(proposal_shared_dir, os.path.basename(self.data_file) + ".err")

            #MaxChunkSize is set to 32G specifically for the jobs run on fermi, which has 32 nodes and 64GB/node
            #We would like to get MaxChunkSize from an env variable in the future
            
            Chunks = api.DetermineChunking(Filename=self.data_file,MaxChunkSize=32.0)
            nodesDesired = Chunks.rowCount()
            
            logging.info("Chunks: " + str(Chunks))
            logging.info("nodesDesired: " + str(nodesDesired))
            
            if nodesDesired > 32:
                nodesDesired = 32
            
            cmd_out = " -o " + out_log + " -e " + out_err
            cmd_l = " -l nodes=" + str(nodesDesired) + ":ppn=1"
            cmd_v = " -v data_file='" + self.data_file + "',facility='" + self.facility + "',instrument='" + self.instrument + "',proposal_shared_dir='" + proposal_shared_dir + "'"
            cmd_job = " " + self.sw_dir + "/remoteJob.sh"
     
            cmd = "qsub" + cmd_out + cmd_l + cmd_v + cmd_job

            #cmd = "qsub -v data_file='" + self.data_file + "',facility='" + self.facility + "',instrument='" + self.instrument + "',proposal_shared_dir='" + proposal_shared_dir + "' -l nodes=" + str(nodesDesired) + ":ppn=1 " + sw_dir + "/remoteJob.sh"
            logging.info("reduction subprocess started: " + cmd)

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True).stdout.read()
            list = proc.split(".")
            if len(list) > 0:
                pid = list[0].rstrip()

            qstat_pid = "qstat: Unknown Job Id " + pid
            logging.info("qstat_pid: " + qstat_pid)
            
            while True:
              qstat_cmd = "qstat " + pid
              ret = subprocess.Popen(qstat_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True).stdout.read().rstrip()
              logging.info("Popen return code: " + ret)
              if ret.startswith(qstat_pid):
                #logging.info("called /queue/"+self.conf.reduction_complete + " --- " + json.dumps(self.data))     
                break
              else:
                time.sleep(30)

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
        self.client.connect()
        self.client.send(destination, data)
        self.client.disconnect()
    
    
if __name__ == "__main__":
    try:
        conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
        message = sys.argv[1]
        logging.info("message: " + message)
        data = json.loads(message)
        
        try:  
            pp = PostProcessAdmin(data, conf)
            pp.reduce()
            sys.exit()

        except ValueError as e:
            data["error"] = str(e)
            logging.error("JSON data error: " + json.dumps(data))
            stomp = Stomp(StompConfig(conf.brokers, conf.amq_user, conf.amq_pwd))
            stomp.connect()
            stomp.send(conf.postprocess_error, json.dumps(data))
            stomp.disconnect()
            logging.info("Called " + conf.postprocess_error + "----" + json.dumps(data))
            raise
        
        except:
            raise
        
    except:
        sys.exit()
    
