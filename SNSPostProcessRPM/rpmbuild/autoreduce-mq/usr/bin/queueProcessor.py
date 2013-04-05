#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp
from queueListener import Client, Configuration, Listener

post_processing_bin = sys.path.append("/usr/bin") 
os.environ['NEXUSLIB'] = "/usr/lib64/libNeXus.so"

from ingestNexus_mq import IngestNexus
from ingestReduced_mq import IngestReduced


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
            else: 
                data["error"] = "data_file is missing"
                logging.error("error=" + message)
                self._send_connection.send('/queue/'+self.configuration.catalog_error_queue, message)
                return
        except:
            logging.error("Could not process JSON message")
            logging.error(str(sys.exc_value))

 
        if destination == '/queue/REDUCTION.DATA_READY':
            param = path.split("/")
            if len(param) > 5:
                facility = param[1]
                instrument = param[2]
                proposal = param[3]
                out_dir = "/"+facility+"/"+instrument+"/"+proposal+"/shared/autoreduce/"
                #out_dir = "/tmp/shelly/"
                reduce_script = "reduce_" + instrument
                reduce_script_path = "/" + facility + "/" + instrument + "/shared/autoreduce/" + reduce_script  + ".py"
                logging.info("reduce_script: "+reduce_script)
                logging.info("reduce_script_path: "+reduce_script_path)
                logging.info("input file: " + path + "out directory: " + out_dir)
                logging.info("Reduction: " + facility + ", " + instrument)
                try:
                    logging.info("Calling /queue/"+self.configuration.reduction_started_queue)             
                    self._send_connection.send('/queue/'+self.configuration.reduction_started_queue, message)
                    m = imp.load_source(reduce_script, reduce_script_path)
                    reduction = m.AutoReduction(path, out_dir)
                    reduction.execute()
                    self._send_connection.send('/queue/'+self.configuration.reduction_complete_queue, message)
                except RuntimeError, e:
                    logging.info("REDUCTION RuntimeError")
                    data["error"] = "REDUCTION RuntimeError: %s " % e 
                    self._send_connection.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))
                except KeyError, e:
                    logging.info("REDUCTION KeyError")
                    data["error"] = "REDUCTION KeyError: %s " % e 
                    self._send_connection.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))
                except Exception, e:
                    logging.info("REDUCTION Exception")
                    data["error"] = "REDUCTION Error: %s " % e 
                    self._send_connection.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))
            
            else:
                data["error"] = "REDUCTION Error: failed to parse data_file " + path
                logging.info("Calling /queue/"+self.configuration.reduction_error_queue + json.dumps(data))     
                self._send_connection.send('/queue/'+self.configuration.reduction_error_queue, json.dumps(data))

        elif destination == '/queue/CATALOG.DATA_READY':
            try:
                self._send_connection.send('/queue/'+self.configuration.catalog_started_queue, message)
                logging.info("path=" + path)
                ingestNexus = IngestNexus(path)
                ingestNexus.execute()
                ingestNexus.logout()
                self._send_connection.send('/queue/'+self.configuration.catalog_complete_queue, message)
            except Exception, e:
                data["error"] = "CATALOG Error: %s" % e
                self._send_connection.send('/queue/'+self.configuration.catalog_error_queue, json.dumps(data))

        elif destination == '/queue/REDUCTION_CATALOG.DATA_READY':
            param = path.split("/")
            if len(param) > 5:
                facility = param[1]
                instrument = param[2]
                ipts = param[3]
                filename = param[5]
                
                param2 = filename.split(".")
                if len(param2) > 2:
                    param3 = param2[0].split("_")
                    if len(param3) > 1:
                        run_number = param3[1]
                        try:
                            logging.info("Reduction Catalog: " + facility + ", " + instrument + ", " + ipts + ", " + run_number)
                            self._send_connection.send('/queue/'+self.configuration.reduction_catalog_started_queue, message)
                            ingestReduced = IngestReduced(facility, instrument, ipts, run_number)
                            ingestReduced.execute()
                            ingestReduced.logout()
                            self._send_connection.send('/queue/'+self.configuration.reduction_catalog_complete_queue, message)
                        except Exception, e:
                            data["error"] = "REDUCTION_CATALOG Catalog Error: %s" % e
                            self._send_connection.send('/queue/'+self.configuration.reduction_catalog_error_queue, json.dumps(data))

            else:
                data["error"] = "REDUCTION_CATALOG Error: failed to parse data_file " + path
                logging.info("Calling /queue/"+self.configuration.reduction_catalog_error_queue + json.dumps(data))     
                self._send_connection.send('/queue/'+self.configuration.reduction_catalog_error_queue, json.dumps(data))

        
        print "Done with post processing"


def run():
    """
    Run an instance of the Post Process ActiveMQ consumer
    """
    # Look for configuration
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')

    queues = conf.queues
    #queues.append(conf.catalog_data_ready_queue)
    
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd,
               queues, "post_process_consumer")
    c.set_listener(PostProcessListener(conf))
    c.listen_and_wait(0.1)

if __name__ == "__main__":
    run()
