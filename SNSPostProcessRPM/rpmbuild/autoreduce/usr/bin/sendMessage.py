import sys
import stomp
import json
import time


def send(destination, message, persistent='true'):
    """
    Send a message to a queue
    @param destination: name of the queue
    @param message: message content
    """

    config_file = '/etc/autoreduce/post_process_consumer.conf'
    if config_file is not None and os.path.exists(config_file):
        cfg = open(config_file, 'r')
        json_encoded = cfg.read()
        try:
            config = json.loads(json_encoded)

            if type(config)==dict:

            if config.has_key('amq_user'):
                icat_user = config['amq_user']

            if config.has_key('amq_pwd'):
                icat_passcode = config['amq_pwd']

            if config.has_key('brokers'):
                 brokers = config['brokers']

        except:
            logging.error("Could not read configuration file:\n %s" % str(sys.exc_value))
    elif config_file is not None:
        logging.error("Could not find configuration: %s" % config_file)

    conn = stomp.Connection(host_and_ports=brokers,
                    user=icat_user, passcode=icat_passcode,
                    wait_on_receipt=True)
    conn.start()
    conn.connect()
    conn.send(destination=destination, message=message, persistent=persistent)
    print "%s: %s" % ("destination", destination)
    print "%s: %s" % ("message", message)

    conn.disconnect()

destination = "/queue/POSTPROCESS.DATA_READY"
send(destination, sys.argv[1])
