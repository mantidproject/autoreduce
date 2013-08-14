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
#sys.argv[1] is passed in by TS as "/facil/instr/ipts/coll_number/run_number/"
file = sys.argv[1]
token = file.rstrip("/").split("/")

if len(token) == 6:
    facility = token[1]
    instrument = token[2]
    ipts = token[3] 
    run_number = token[5]  #skip token[4] which is collection number 
    data_file = file + "NeXus/" + instrument + "_" + run_number + "_event.nxs" 
    data = {"facility": facility, "instrument": instrument, "ipts": ipts, "run_number": run_number, "data_file":  data_file}

    message = json.dumps(data)
    logging.info("Sending message: " + message + " to " + destination)
    send(destination, message)
else:
    logging.error("legacy data input error: expecting a file path as /SNS/NOM/IPTS-8951/0/17172")
    sys.exit() 
