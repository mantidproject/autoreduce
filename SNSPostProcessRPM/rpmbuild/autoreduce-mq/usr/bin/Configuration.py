"""
Base ActiveMQ consumer class
"""
import time, stomp, logging, json, os, sys, threading, socket
from PostProcessQueueConnector import PostProcessQueueConnector


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

    def get_client(self, client_name='post_process_consumer', queues=[]):
        """
        Return a configured ActiveMQ client
        @param client_name: name of the client
        @param queues: list of queues to be added to default list of queues
        """
        return PostProcessQueueConnector(self.brokers, self.amq_user, self.amq_pwd, queues, client_name)
