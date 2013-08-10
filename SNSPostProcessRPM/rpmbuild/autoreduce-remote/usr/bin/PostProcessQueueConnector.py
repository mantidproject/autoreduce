#!/usr/bin/env python
"""
Post Process Queue Connector. It listens and sends messages to the acticeMQ.
"""
import time, stomp, logging, json, sys, socket
from Listener import Listener

class PostProcessQueueConnector(object):
    """
    ActiveMQ QueueConnector
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
        Disconnect and stop the QueueConnector
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
            logging.error("Problem starting AMQ QueueConnector: %s" % sys.exc_value)

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

