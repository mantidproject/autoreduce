"""
Base ActiveMQ consumer class
"""
import time, stomp, logging, json, os, sys, threading, socket

class Listener(stomp.ConnectionListener):
    """
    Base listener class for an ActiveMQ client
    A fully implemented class should overload the on_message() method to process incoming messages.
    """

    def __init__(self, configuration=None, connection=None,
                 results_ready_queue=None):
        """
        @param configuration: Configuration object
        @param connection: Connection object
        @param results_ready_queue: Overwrite the name of the results-ready queue
        """
            
        self.configuration = configuration
        self.connection = connection

    def on_message(self, headers, message):
        """
        Process a message.
        @param headers: message headers
        @param message: JSON-encoded message content
        """
        logging.info("Processing a message: %s" % message)
        
class Client(object):
    """
    ActiveMQ client
    Holds the connection to a broker
    """
    
    def __init__(self, brokers, user, passcode,
                 queues=None, consumer_name="amq_consumer"):
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
        Set the listener object that will process each incoming message.
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
        This method will simply return once the connection is terminated.
        @param waiting_period: sleep time between connection to a broker
        """
        try:
            self.connect()
        except:
            logging.error("Problem starting AMQ client: %s" % sys.exc_value)

        last_heartbeat = 0
        while(True):
            try:
                if self._connection is None or self._connection.is_connected() is False:
                    self.connect()
                    
                time.sleep(waiting_period)
                
                try:
                    if time.time()-last_heartbeat>5:
                        last_heartbeat = time.time()
                        data_dict = {"src_name": socket.gethostname(),
                                     "status": "0"}
                        message = json.dumps(data_dict)
                        self._connection.send(destination="/topic/SNS.COMMON.STATUS.AUTOREDUCE.0",
                                              message=message,
                                              persistent='true')
                except:
                    logging.error("Problem sending heartbeat")
                
            except:
                logging.error("Problem connecting to AMQ broker")
                time.sleep(5.0)
            
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

class Configuration(object):
    """
        Read and process configuration file and provide an easy way to create a configured Client object
    """
    # Dummy ActiveMQ settings for testing
    amq_user = 'icat'
    amq_pwd = 'icat'
    brokers = [('localhost', 61613)]
    queues = ['foo.bar']


    def __init__(self, config_file=None):
        # Look for configuration
        if config_file is not None and os.path.exists(config_file):
            logging.info("found configuration file at: %s" % config_file)
            cfg = open(config_file, 'r')
            json_encoded = cfg.read()
            try:
                config = json.loads(json_encoded)
            
                if type(config)==dict:
                    
                    if config.has_key('amq_user'):
                        self.amq_user = config['amq_user']
                        
                    if config.has_key('amq_pwd'):
                        self.amq_pwd = config['amq_pwd']
                    
                    if config.has_key('brokers'):
                        brokers = config['brokers']
                        self.brokers = []
                        for b in brokers:
                            self.brokers.append( (b[0], b[1]) )
                    
                    if config.has_key('amq_queues'):
                        self.queues = config['amq_queues']
                        
                    if config.has_key('postprocess_error'):
                        self.postprocess_error = config['postprocess_error']
                        
                    if config.has_key('catalog_started'):
                        self.catalog_started = config['catalog_started']
                        
                    if config.has_key('catalog_complete'):
                        self.catalog_complete = config['catalog_complete']
                        
                    if config.has_key('catalog_error'):
                        self.catalog_error = config['catalog_error']
                        
                    if config.has_key('reduction_started'):
                        self.reduction_started = config['reduction_started']
                                            
                    if config.has_key('reduction_complete'):
                        self.reduction_complete = config['reduction_complete']
                                            
                    if config.has_key('reduction_error'):
                        self.reduction_error = config['reduction_error']
                        
                    if config.has_key('reduction_catalog_started'):
                        self.reduction_catalog_started = config['reduction_catalog_started']
                                            
                    if config.has_key('reduction_catalog_complete'):
                        self.reduction_catalog_complete = config['reduction_catalog_complete']
                                            
                    if config.has_key('reduction_catalog_error'):
                        self.reduction_catalog_error = config['reduction_catalog_error']
                        
                    if config.has_key('log_file'):
                        self.log_file = config['log_file']
                        
            except:
                logging.error("Could not read configuration file:\n %s" % str(sys.exc_value))
        elif config_file is not None:
            logging.error("Could not find configuration: %s" % config_file)

    def get_client(self, client_name='bare_client', queues=[]):
        """
        Return a configured ActiveMQ client
        @param client_name: name of the client
        @param queues: list of queues to be added to default list of queues
        """
        return Client(self.brokers, self.amq_user, self.amq_pwd, queues, client_name)
