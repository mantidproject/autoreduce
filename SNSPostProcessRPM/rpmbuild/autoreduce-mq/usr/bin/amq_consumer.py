"""
    ActiveMQ consumer class
    
    TODO: error and info messages are mixed up (used to be prints in queueListener.py)
"""
import time
import stomp
import logging
import json
import os
import sys
import imp    

post_processing_bin = sys.path.append("/usr/bin") 
os.environ['NEXUSLIB'] = "/usr/lib64/libNeXus.so"

from ingestNexus_mq import IngestNexus
from ingestReduced_mq import IngestReduced

class Listener(stomp.ConnectionListener):
    """
        Listener class for an ActiveMQ client
    """
    def __init__(self, config):
        #TODO: use config info rather than hard-coding
        
        # List of queues used
        self._reduction_data_ready_queue = '/queue/REDUCTION.DATA_READY'
        self._reduction_started_queue    = '/queue/REDUCTION.STARTED'
        self._reduction_complete_queue   = '/queue/REDUCTION.COMPLETE'
        self._error_queue                = '/queue/POSTPROCESS.ERROR'
        self._catalog_data_ready_queue   = '/queue/CATALOG.DATA_READY'
        self._catalog_started_queue      = '/queue/CATALOG.STARTED'
        self._catalog_complete_queue     = '/queue/CATALOG.COMPLETE'
        self._reduction_cat_data_ready_queue = '/queue/REDUCTION_CATALOG.DATA_READY'
        self._reduction_cat_started_queue    = '/queue/REDUCTION_CATALOG.STARTED'
        self._reduction_cat_complete_queue   = '/queue/REDUCTION_CATALOG.COMPLETE'

        
    def on_message(self, headers, message):
        logging.info("<--- %s: %s" % (headers["destination"], message))
        destination = headers["destination"]
        data = json.loads(message)
        
        if data.has_key('data_file'):
            path = str(data['data_file'])
        else: 
            data["error"] = "data_file is missing"
            logging.error("Calling %s with message %s " % (self._error_queue, 
                                                          json.dumps(data)))
            self.send(self._error_queue, json.dumps(data), persistent='true')
            return
        
        if destination == self._reduction_data_ready_queue:
            param = path.split("/")
            if len(param) > 5:
                facility = param[1]
                instrument = param[2]
                proposal = param[3]
                out_dir = "/"+facility+"/"+instrument+"/"+proposal+"/shared/autoreduce/"
                reduce_script = "reduce_" + instrument
                reduce_script_path = "/" + facility + "/" + instrument + "/shared/autoreduce/" + reduce_script + ".py"
                logging.info("reduce_script: %s" % reduce_script)
                logging.info("reduce_script_path: %s" % reduce_script_path)
                logging.info("input file: %s: out directory: %s" % (path, out_dir))
                try:
                    logging.info("Calling %s with message %s" % (self._reduction_started_queue,
                                                                 message))
                    self.send(self._reduction_started_queue, message, persistent='true')
                    m = imp.load_source(reduce_script, reduce_script_path)
                    reduction = m.AutoReduction(path, out_dir)
                    reduction.execute()
                    queue = self._reduction_complete_queue
                except RuntimeError, e:
                    data["error"] = "REDUCTION RuntimeError: " + ''.join(e) 
                    queue = self._error_queue
                except KeyError, e:
                    data["error"] = "REDUCTION KeyError: " + ''.join(e)
                    queue = self._error_queue
                except Exception, e:
                    data["error"] = "REDUCTION Error: " + ''.join(e)
                    queue = self._error_queue
                finally:
                    logging.info("Calling %s with message %s " % (queue, json.dumps(data)))
                    self.send(queue, json.dumps(data), persistent='true')
            else:
                data["error"] = "REDUCTION Error: failed to parse data_file " + path
                logging.error("Calling %s with message %s" % (self._error_queue, json.dumps(data)))
                self.send(self._error_queue, json.dumps(data), persistent='true')

        elif destination == self._catalog_data_ready_queue:
            try:
                self.send(self._catalog_started_queue, message, persistent='true')
                ingestNexus = IngestNexus(path)
                ingestNexus.execute()
                ingestNexus.logout()
                queue = self._catalog_complete_queue
            except Exception, e:
                    data["error"] = "CATALOG Error: " + ''.join(e)
                    queue = self._error_queue
            finally:
                    logging.info("Calling %s with message %s " % (queue, json.dumps(data)))
                    self.send(queue, json.dumps(data), persistent='true')

        elif destination == self._reduction_cat_data_ready_queue:
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
                            logging.info("Reduction Catalog: %s %s %s %s" % (facility, instrument, ipts, run_number))
                            self.send(self._reduction_cat_started_queue, message, persistent='true')
                            ingestReduced = IngestReduced(facility, instrument, ipts, run_number)
                            ingestReduced.execute()
                            ingestReduced.logout()
                            queue = self._reduction_cat_complete_queue
                        except Exception, e:
                            data["error"] = "REDUCTION_CATALOG Catalog Error: " + ''.join(e)
                            queue = self._error_queue
                        finally:
                            logging.info("Calling %s with message %s " % (queue, json.dumps(data)))
                            self.send(queue, json.dumps(data), persistent='true')
            else:
                data["error"] = "REDUCTION_CATALOG Error: failed to parse data_file " + path
                logging.error("Calling %s with message %s " % (self._error_queue, json.dumps(data)))
                self.send(self._error_queue, json.dumps(data), persistent='true')

class Client(object):
    """
        ActiveMQ client
        Holds the connection to a broker
    """
    
    def __init__(self, brokers, user, passcode, 
                 queues=None, consumer_name="autoreduce_consumer"):
        """ 
            @param brokers: list of brokers we can connect to
            @param user: activemq user
            @param passcode: passcode for activemq user
            @param queues: list of queues to listen to
            @param consumer_name: name of the AMQ listener
        """
        self._brokers = brokers
        self._user = user
        self._passcode = passcode
        self._connection = None
        self._connected = False        
        self._queues = queues
        self._consumer_name = consumer_name
        self._listener = None
        
    def set_listener(self, listener):
        """
            Set the listener object that will process each
            incoming message.
            @param listener: listener object
        """
        self._listener = listener
        
    def get_connection(self, listener=None):
        """
            Establish and return a connection to ActiveMQ
            @param listener: listener object
        """
        if listener is None:
            if self._listener is None:
                listener = Listener()
            else:
                listener = self._listener

        logging.info("[%s] Attempting to connect to ActiveMQ broker" % self._consumer_name)
        conn = stomp.Connection(host_and_ports=self._brokers, 
                                user=self._user,
                                passcode=self._passcode, 
                                wait_on_receipt=True)
        conn.set_listener(self._consumer_name, listener)
        conn.start()
        conn.connect()        
        return conn
            
    def connect(self):
        """
            Connect to a broker
        """
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
        
        logging.info("[%s] Subscribing to %s" % (self._consumer_name,
                                                 str(self._queues)))
        for q in self._queues:
            self._connection.subscribe(destination=q, ack='auto', persistent='true')
        self._connected = True
    
    def _disconnect(self):
        """
            Clean disconnect
        """
        if self._connection is not None and self._connection.is_connected():
            self._connection.disconnect()
        self._connection = None
        
    def stop(self):
        """
            Disconnect and stop the client
        """
        self._disconnect()
        if self._connection is not None:
            self._connection.stop()
        self._connection = None
        self._connected = False
        
    def listen_and_wait(self, waiting_period=1.0):
        """
            Listen for the next message from the brokers.
            This method will simply return once the connection is
            terminated.
            @param waiting_period: sleep time between connection to a broker
        """
        self.connect()
        while(self._connected):
            time.sleep(waiting_period)
            
    def send(self, destination, message, persistent='true'):
        """
            Send a message to a queue
            @param destination: name of the queue
            @param message: message content
        """
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
        self._connection.send(destination=destination, message=message, persistent=persistent)
