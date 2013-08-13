import sys, os, logging
import stomp
import json
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
    filename="/var/log/SNS_applications/post_process.log",
    filemode='a'
)

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

            if config.has_key('amq_user'):
                user = config['amq_user']

            if config.has_key('amq_pwd'):
                passcode = config['amq_pwd']

            if config.has_key('brokers'):
                brokers = config['brokers']
                print brokers
                brokersFormated = []
                for b in brokers:
                    brokersFormated.append( (b[0], b[1]) )

        except:
            logging.error("Could not read configuration file: " + str(sys.exc_value))
    elif config_file is not None:
        logging.error("Could not find configuration: " + config_file)

    conn = stomp.Connection(host_and_ports=brokersFormated,
                    user=user, passcode=passcode,
                    wait_on_receipt=True)
    conn.start()
    conn.connect()
    conn.send(destination=destination, message=message, persistent=persistent)
    logging.info("destination: " + destination)
    logging.info("message: " + message)

    conn.disconnect()

destination = "POSTPROCESS.DATA_READY"
send(destination, sys.argv[1])
