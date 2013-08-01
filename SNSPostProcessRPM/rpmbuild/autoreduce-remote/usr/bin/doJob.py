#!/usr/bin/env python
"""
ActiveMQ client for Post Process
"""
import os, sys, json, logging, imp, subprocess
from string import join
from queueListener import Client, Configuration, Listener

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
    

def main(facility, instrument, proposal, run_number, data_file):
    logging.info("doJob:" + "facility=" + facility + "instrument=" + instrument + "proposal=" + proposal + "runNumber=" + run_number + "data_file=" + data_file)
        
    # Create a configuration object
    conf = Configuration('/etc/autoreduce/post_process_consumer.conf')
    c = Client(conf.brokers, conf.amq_user, conf.amq_pwd,
               conf.queues,  "post_process_consumer")

    logging.info("Calling /queue/REDUCTIONSTARTED"+data_file)             
    c.send('/queue/REDUCTION.STARTED', data_file)
    
    sw_dir = '/sw/fermi/autoreduce/scripts' 
    
    #log_dir = "/" + facility + "/" + instrument + "/" + proposal + "/shared/autoreduce"
    log_dir = "/tmp/work/3qr/autoreduce"
    out_dir = log_dir + "/reduction_log/"
    logging.info("out_dir=" + out_dir)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
                
    err_dir = log_dir
    logging.info("input file: " + data_file + ", out directory: " + out_dir)
            
    try:
        #MaxChunkSize is set to 32G specifically for the jobs run on fermi, which has 32 nodes and 64GB/node
        #We would like to get MaxChunkSize from an env variable in the future
            
        Chunks = api.DetermineChunking(Filename=data_file,MaxChunkSize=32.0)
        nodesDesired = Chunks.rowCount()
        logging.info("nodesDesired: " + str(nodesDesired))
            
        if nodesDesired > 32:
            nodesDesired = 32
            
        c.send('/queue/REDUCTION.STARTED', data_file )
        #c.send('/queue/'+conf.reduction_start_queue, data_file )
                
        cmd = "qsub -v data_file='" + data_file + "',facility='" + facility + "',instrument='" + instrument + "',out_dir='" + out_dir + "' -l nodes=" + str(nodesDesired) + ":ppn=1 " + sw_dir + "/remoteJob.sh"
        logging.info("cmd: " + cmd)
        out_log = os.path.join(out_dir, instrument + "_" + run_number + ".log")
        out_err = os.path.join(err_dir, instrument + "_" + run_number + ".err")
        logFile=open(out_log, "w")
        errFile=open(out_err, "w")
        proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=logFile, stderr=errFile, universal_newlines = True)
        proc.communicate()
        logFile.close()
        errFile.close()
        #logging.info("Calling /queue/"+conf.reduction_complete_queue+data_file)             
        logging.info("Calling /queue/REDUCTION.COMPLETE"+data_file)             
        c.send('/queue/REDUCTION.COMPLETE', data_file)
        #c.send('/queue/'+conf.reduction_complete_queue, data_file)
            
    except Exception, e:
        error = "REDUCTION: %s " % e 
        logging.error("Calling /queue/REDUCTION.COMPLETE" + error)
        c.send('/queue/REDUCTION.COMPLETE', error)
            
    logging.info("Done with reduction on fermi")
    c._disconnect()
    
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
