"""
Queue Configuration 
"""
import logging, json, sys, os, socket

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
stderr_logger = logging.getLogger('STDERR')
sl = StreamToLogger(stderr_logger, logging.ERROR)
sys.stderr = sl

class Configuration(object):
    """
        Read and process configuration file and provide an easy way to create a configured Client object
    """
    def __init__(self, config_file):
        
        try:
            if os.access(config_file, "R_OK") == "False":
                logging.error("configuration file doesn't exist or is not readable")
                raise
            else:
                logging.info("found configuration file at: %s" % config_file)
                cfg = open(config_file, 'r')
                json_encoded = cfg.read()           
                config = json.loads(json_encoded)
                self.amq_user = config['amq_user']
                self.amq_pwd = config['amq_pwd']
                self.brokers = config['brokers']
                self.queues = config['amq_queues']
                self.postprocess_error = config['postprocess_error']
                self.catalog_started = config['catalog_started']
                self.catalog_complete = config['catalog_complete']
                self.catalog_error = config['catalog_error']
                self.reduction_started = config['reduction_started']
                self.reduction_complete = config['reduction_complete']
                self.reduction_error = config['reduction_error']
                self.reduction_catalog_started = config['reduction_catalog_started']
                self.reduction_catalog_complete = config['reduction_catalog_complete']
                self.reduction_catalog_error = config['reduction_catalog_error']
                self.heart_beat = config['heart_beat']
        except:
            logging.error("Could not read configuration file:\n %s" % str(sys.exc_value))
            