import json, logging, socket, os, subprocess
from string import join

from ingestNexus_mq import IngestNexus
from ingestReduced_mq import IngestReduced
from queueListener import Client

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
    filename='/var/log/SNS_applications/post_process.log',
    filemode='a'
)
  

class PostProcess:
    def __init__(self, data, conf):

        self.data = data
        self.data["information"] = socket.gethostname()
        logging.info("json data: " + str(self.data))
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


    def catalogRaw(self):
        try:
            logging.info("called /queue/" + self.conf.catalog_started + " --- " + json.dumps(self.data))  
            self.send('/queue/'+self.conf.catalog_started, json.dumps(self.data))
            ingestNexus = IngestNexus(self.data_file)
            ingestNexus.execute()
            ingestNexus.logout()
            self.send('/queue/'+self.conf.catalog_complete, json.dumps(self.data))  
            logging.info("called /queue/"+self.conf.catalog_complete + " --- " + json.dumps(self.data))     
        except Exception, e:
            self.data["error"] = "CATALOG Error: %s" % e
            logging.error("called /queue/"+self.conf.catalog_error  + " --- " + json.dumps(self.data))
            self.send('/queue/'+self.conf.catalog_error, json.dumps(self.data))
            
    def catalogReduced(self):
        try:
            logging.info("called /queue/" + self.conf.reduction_catalog_started + " --- " + json.dumps(self.data))  
            self.send('/queue/'+self.conf.reduction_catalog_started, self.data)
            ingestReduced = IngestReduced(self.facility, self.instrument, self.proposal, self.run_number)
            ingestReduced.execute()
            ingestReduced.logout()
            self.send('/queue/'+self.conf.reduction_catalog_complete , json.dumps(self.data))  
            logging.info("called /queue/"+self.conf.reduction_catalog_complete + " --- " + json.dumps(self.data))   
        except Exception, e:
            self.data["error"] = "REDUCTION_CATALOG Error: %s" % e
            logging.error("called /queue/"+self.conf.reduction_catalog_error  + " --- " + json.dumps(self.data))
            self.send('/queue/'+self.conf.reduction_catalog_error , json.dumps(self.data))
            
        
    def reduce(self):
        try:         
            self.send('/queue/'+self.conf.reduction_started, json.dumps(self.data))  
            logging.info("called /queue/" + self.conf.reduction_started + " --- " + json.dumps(self.data))  

            instrument_shared_dir = "/" + self.facility + "/" + self.instrument + "/shared/autoreduce/"
            #instrument_shared_dir = "/tmp/shelly2/"
            reduce_script = "reduce_" + self.instrument
            reduce_script_path = instrument_shared_dir + reduce_script  + ".py"
            
            proposal_shared_dir = "/" + self.facility + "/" + self.instrument + "/" + self.proposal + "/shared/autoreduce/"
            #proposal_shared_dir = "/tmp/shelly2/"
            log_dir = proposal_shared_dir + "reduction_log/"

            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            cmd = "python " + reduce_script_path + " " + self.data_file + " " + proposal_shared_dir
            logging.info("reduction started: " + cmd)
            out_log = os.path.join(log_dir, os.path.basename(self.data_file) + ".log")
            out_err = os.path.join(proposal_shared_dir, os.path.basename(self.data_file) + ".err")
            logFile=open(out_log, "w")
            errFile=open(out_err, "w")
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=logFile, stderr=errFile, universal_newlines = True)
            proc.communicate()
            logFile.close()
            errFile.close()
            logging.info("reduction completed")
            
            if os.stat(out_err).st_size == 0:
                os.remove(out_err)
                self.send('/queue/'+self.conf.reduction_complete , json.dumps(self.data))  
                logging.info("called /queue/"+self.conf.reduction_complete + " --- " + json.dumps(self.data))     
            else:
                errFile=open(out_err, "r")
                errList = errFile.readlines()
                try:                     
                    idx = errList.index("    raise e\n")+1
                except ValueError:
                    idx = 0
                self.data["error"] = "REDUCTION: %s " % join(errList[idx:])
                errFile.close()
                self.send('/queue/'+self.conf.reduction_error , json.dumps(self.data))
                logging.error("called /queue/"+self.conf.reduction_error  + " --- " + json.dumps(self.data))       

        except Exception, e:
            self.data["error"] = "REDUCTION Error: %s " % e 
            logging.error("called /queue/"+self.conf.reduction_error  + " --- " + json.dumps(self.data))
            self.send('/queue/'+self.conf.reduction_error , json.dumps(self.data))
            

    def send(self, destination, data):
        c = Client(self.conf.brokers, self.conf.amq_user, self.conf.amq_pwd, self.conf.queues, "post_process_consumer")
        c.send(destination, json.dumps(self.data))
        
    
    def getData(self):
        return self.data
