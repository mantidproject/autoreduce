import time
import stomp
import logging
import json

class Listener(stomp.ConnectionListener):
    """ Base listener class for an ActiveMQ client
        A fully implemented class should overload
        the on_message() method to process incoming messages.
    """

    def __init__(self, configuration=None):
        super(Listener, self).__init__()
        
    def on_message(self, headers, message):
        """ Process a message
            @param headers: message headers
            @param message: JSON-encoded message content
        """

        # The headers contains the queue or topic:
        destination = headers["destination"]
        
        # If you passed JSON-encoded data with your message,
        # the following can be used to transform it to a dictionary
        try:
            data_dict = json.loads(message)
        except:
            logging.error("Could not decode message from %s" % headers["destination"])
            return
