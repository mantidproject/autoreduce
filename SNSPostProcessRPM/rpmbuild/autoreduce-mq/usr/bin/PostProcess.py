import json, socket, os, subprocess, logging, sys

from ingestNexus_mq import IngestNexus
from ingestReduced_mq import IngestReduced
from queueListener import Client, Configuration
 
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


                
class PostProcess:
    def __init__(self, data, conf):

        os.environ['NEXUSLIB'] = "/usr/lib64/libNeXus.so"
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
            #instrument_shared_dir = "/" + self.facility + "/" + self.instrument + "/shared/autoreduce/"
            instrument_shared_dir = "/tmp/shelly2/"
            reduce_script = "reduce_" + self.instrument
            reduce_script_path = instrument_shared_dir + reduce_script  + ".py"
            
            #proposal_shared_dir = "/" + self.facility + "/" + self.instrument + "/" + self.proposal + "/shared/autoreduce/"
            proposal_shared_dir = "/tmp/shelly2/"
            log_dir = proposal_shared_dir + "reduction_log/"

            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            cmd = "python " + reduce_script_path + " " + self.data_file + " " + proposal_shared_dir
            logging.info("reduction subprocess started: " + cmd)
            out_log = os.path.join(log_dir, os.path.basename(self.data_file) + ".log")
            out_err = os.path.join(proposal_shared_dir, os.path.basename(self.data_file) + ".err")
            logFile=open(out_log, "w")
            errFile=open(out_err, "w")
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=logFile, stderr=errFile, universal_newlines = True)
            proc.communicate()
            logFile.close()
            errFile.close()
            logging.info("reduction subprocess completed")
            
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
    
    
if __name__ == "__main__":
    try:
        destination, message = sys.argv[1:3]
        logging.info("destination: " + destination)
        logging.info("message: " + message)
        data = json.loads(message)
        logging.info("data: " + str(data))
    except ValueError as e:
        data["error"] = str(e)
        logging.error("JSON data is incomplete: " + json.dumps(data) )
        self._send_connection.send("/queue/POSTPROCESS.ERROR", json.dumps(data))
        logging.info("Called /queue/POSTPROCESS.ERROR -- JSON data is incomplete: " + json.dumps(data))

    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
        
    pp = PostProcess(data, conf)
    if destination == '/queue/REDUCTION.DATA_READY':
        pp.reduce()

    elif destination == '/queue/CATALOG.DATA_READY':
        pp.catalogRaw()

    elif destination == '/queue/REDUCTION_CATALOG.DATA_READY':
        pp.catalogReduced()
        
    sys.exit()




