import stomp, logging, logging.config, smtplib, orm_mapping, datetime
import time, sys, os, json, glob, base64
from settings import ACTIVEMQ, LOGGING, MYSQL, ICAT, LOG_FILE
from icat_communication import ICATCommunication
from mysql_client import MySQL
from base import engine, session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect
from orm_mapping import *
import traceback

# Set up logging and attach the logging to the right part of the config.
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("queue_processor")


class Listener(object):
    def __init__(self, client):
        logger.info("INIT")
        self._client = client
        self._data_dict = {}
        self._priority = ''

    def on_error(self, headers, message):
        logger.info("ON ERROR")
        logger.error("Error received - %s" % str(message))

    def on_message(self, headers, message):
        logger.info("ON MESSAGE")
        destination = headers["destination"]
        self._priority = headers["priority"]
        logger.info("Dest: %s Prior: %s" % (destination, self._priority))
        # Load the JSON message and header into dictionaries
        try:
            self._data_dict = json.loads(message)
        except:
            logger.error("Could not decode message from %s" % destination)
            logger.error(sys.exc_value)
            return
        try:
            if destination == '/queue/DataReady':
                self.data_ready()
            elif destination == '/queue/ReductionStarted':
                self.reduction_started()
            elif destination == '/queue/ReductionComplete':
                self.reduction_complete()
            elif destination == '/queue/ReductionError':
                self.reduction_error()
            else:
                logger.warning("Recieved a message on an unknown topic '%s'" % destination)
        except Exception as e:
            logger.error("UNCAUGHT ERROR: %s - %s" % (type(e).__name__, str(e)))
            logger.error(traceback.format_exc())

    def data_ready(self):
        # Rollback the session to avoid getting caught in a loop where we have uncommitted changes causing problems
        session.rollback()
        from process_utils import InstrumentVariablesUtils

        # Strip information from the JSON file (_data_dict)
        run_no = str(self._data_dict['run_number'])
        instrument_name = str(self._data_dict['instrument'])

        logger.info("Data ready for processing run %s on %s" % (run_no, instrument_name))

        # Check if the instrument is active or not in the MySQL database
        instrument = session.query(Instrument).filter_by(name=instrument_name).first()

        # Add the instrument if it doesn't exist
        if not instrument:
            instrument = Instrument(name=instrument_name,
                                    is_active=1,
                                    is_paused=0
                                    )
            session.add(instrument)
            session.commit()
            instrument = session.query(Instrument).filter_by(name=instrument_name).first()
        
        # Activate the instrument if it is currently set to inactive
        if not instrument.is_active:
            instrument.is_active = 1
            session.commit()
        
        # If the instrument is paused, we need to find the 'Skipped' status
        if instrument.is_paused:
            status = session.query(StatusID).filter_by(value='Skipped').first()

        # Else we need to find the 'Queued' status number
        else:
            status = session.query(StatusID).filter_by(value='Queued').first()

        # If there has already been an autoreduction job for this run, we need to know it so we can increase the version
        # by 1 for this job. However, if not then we will set it to -1 which will be incremented to 0
        last_run = session.query(ReductionRun).filter_by(run_number=run_no).order_by('-run_version').first()
        if last_run is not None:
            highest_version = last_run.run_version
        else:
            highest_version = -1
        run_version = highest_version + 1

        # Search for the experiment, if it doesn't exist then add it
        experiment = session.query(Experiment).filter_by(reference_number=run_no).first()
        if experiment is None:
            new_exp = Experiment(reference_number=run_no)
            session.add(new_exp)
            session.commit()
            experiment = session.query(Experiment).filter_by(reference_number=run_no).first()

        # Get the script text for the current instrument. If the script text is null then send to error queue
        script_text = InstrumentVariablesUtils().get_current_script_text(instrument.name)[0]
        if script_text is None:
            self.reduction_error()
            return
        
        # Make the new reduction run with the information collected so far and add it into the database
        reduction_run = ReductionRun( run_number=self._data_dict['run_number']
                                    , run_version=run_version
                                    , run_name=''
                                    , message=''
                                    , cancel=0
                                    , hidden_in_failviewer=0
                                    , admin_log=''
                                    , reduction_log=''
                                    , created=datetime.datetime.now()
                                    , last_updated=datetime.datetime.now()
                                    , experiment_id=experiment.id
                                    , instrument_id=instrument.id
                                    , status_id=status.id
                                    , script=script_text
                                    )
        session.add(reduction_run)
        session.commit()

        # Set our run_version to be the one we have just calculated
        self._data_dict['run_version'] = reduction_run.run_version

        # Create a new data location entry which has a foreign key linking it to the current reduction run. The file
        # path itself will point to a datafile (e.g. "\isis\inst$\NDXWISH\Instrument\data\cycle_17_1\WISH00038774.nxs")
        data_location = DataLocation(file_path=self._data_dict['data'], reduction_run_id=reduction_run.id)
        session.add(data_location)
        session.commit()

        # We now need to create all of the variables for the run such that the script can run through in the desired way
        logger.info('Creating variables for run')
        variables = InstrumentVariablesUtils().create_variables_for_run(reduction_run)
        if not variables:
            logger.warning("No instrument variables found on %s for run %s" % (instrument.name, self._data_dict['run_number']))
        
        logger.info('Getting script and arguments')
        reduction_script, arguments = ReductionRunUtils().get_script_and_arguments(reduction_run)
        self._data_dict['reduction_script'] = reduction_script
        self._data_dict['reduction_arguments'] = arguments
        
        if instrument.is_paused:
            logger.info("Run %s has been skipped" % self._data_dict['run_number'])
        else:
            self._client.send('/queue/ReductionPending', json.dumps(self._data_dict), priority=self._priority)
            logger.info("Run %s ready for reduction" % self._data_dict['run_number'])

    def reduction_started(self):
        logger.info("REDUCTION STARTED")
        logger.info("Run %s has started reduction" % self._data_dict['run_number'])
        
        reduction_run = self.find_run()
        
        if reduction_run:
            if str(reduction_run.status) == "Error" or str(reduction_run.status) == "Queued":
                reduction_run.status = StatusUtils().get_processing()
                reduction_run.started = timezone.now().replace(microsecond=0)
                reduction_run.save()
            else:
                logger.error("An invalid attempt to re-start a reduction run was captured. Experiment: %s, Run Number: %s, Run Version %s" % (self._data_dict['rb_number'], self._data_dict['run_number'], self._data_dict['run_version']))
        else:
            logger.error("A reduction run started that wasn't found in the database. Experiment: %s, Run Number: %s, Run Version %s" % (self._data_dict['rb_number'], self._data_dict['run_number'], self._data_dict['run_version']))

            
    def reduction_complete(self):
        logger.info("REDUCTION COMPLETE")
        try:
            logger.info("Run %s has completed reduction" % self._data_dict['run_number'])
            
            reduction_run = self.find_run()
            
            if reduction_run:
                if reduction_run.status.value == "Processing":
                    reduction_run.status = StatusUtils().get_completed()
                    reduction_run.finished = timezone.now().replace(microsecond=0)
                    for name in ['message', 'reduction_log', 'admin_log']:
                        setattr(reduction_run, name, self._data_dict.get(name, "")) # reduction_run.message = self._data_dict['message']; etc.
                    if 'reduction_data' in self._data_dict:
                        for location in self._data_dict['reduction_data']:
                            reduction_location = ReductionLocation(file_path=location, reduction_run=reduction_run)
                            reduction_run.reduction_location.add(reduction_location)
                            reduction_location.save()
                            
                            # Get any .png files and store them as base64 strings
                            # Currently doesn't check sub-directories
                            graphs = glob.glob(location + '*.[pP][nN][gG]')
                            for graph in graphs:
                                with open(graph, "rb") as image_file:
                                    encoded_string = 'data:image/png;base64,' + base64.b64encode(image_file.read())
                                    if reduction_run.graph is None:
                                        reduction_run.graph = [encoded_string]
                                    else:
                                        reduction_run.graph.append(encoded_string)
                    reduction_run.save()
                    
                    # Trigger any post-processing, such as saving data to ICAT
                    with ICATCommunication() as icat:
                        icat.post_process(reduction_run)                    
                else:
                    logger.error("An invalid attempt to complete a reduction run that wasn't processing has been captured. Experiment: %s, Run Number: %s, Run Version %s" % (self._data_dict['rb_number'], self._data_dict['run_number'], self._data_dict['run_version']))
            else:
                logger.error("A reduction run completed that wasn't found in the database. Experiment: %s, Run Number: %s, Run Version %s" % (self._data_dict['rb_number'], self._data_dict['run_number'], self._data_dict['run_version']))

        except BaseException as e:
            logger.error("Error: %s" % e)
                    

    def reduction_error(self):
        logger.info("REDUCTION ERROR")
        if 'message' in self._data_dict:
            logger.info("Run %s has encountered an error - %s" % (self._data_dict['run_number'], self._data_dict['message']))
        else:
            logger.info("Run %s has encountered an error - No error message was found" % (self._data_dict['run_number']))
        
        reduction_run = self.find_run()
                    
        if not reduction_run:
            logger.error("A reduction run that caused an error wasn't found in the database. Experiment: %s, Run Number: %s, Run Version %s" % (self._data_dict['rb_number'], self._data_dict['run_number'], self._data_dict['run_version']))
            return
        
        reduction_run.status = StatusUtils().get_error()
        reduction_run.finished = timezone.now().replace(microsecond=0)
        for name in ['message', 'reduction_log', 'admin_log']:
            setattr(reduction_run, name, self._data_dict.get(name, "")) # reduction_run.message = self._data_dict['message']; etc.
        reduction_run.save()
        
        if 'retry_in' in self._data_dict:
            self.retryRun(reduction_run, self._data_dict["retry_in"])
            
        self.notifyRunFailure(reduction_run)
        
        
    def find_run(self):
        logger.info("FIND RUN")
        experiment = session.query(Experiment).filter_by(reference_number=self._data_dict['rb_number']).first()
        if not experiment:
            logger.error("Unable to find experiment %s" % self._data_dict['rb_number'])
            return None
        
        reduction_run = session.query(ReductionRun).filter_by(experiment=experiment, run_number=int(self._data_dict['run_number']), run_version=int(self._data_dict['run_version'])).first()
        return reduction_run


    def notifyRunFailure(self, reductionRun):
        logger.info("NOTIFY RUN FAILURE")
        recipients = EMAIL_ERROR_RECIPIENTS
        localRecipients = filter(lambda addr: addr.split('@')[-1] == BASE_URL, recipients) # this does not parse esoteric (but RFC-compliant) email addresses correctly
        if localRecipients: # don't send local emails
            raise Exception("Local email address specified in ERROR_EMAILS - %s match %s" % (localRecipients, BASE_URL))
    
        senderAddress = EMAIL_ERROR_SENDER
        
        errorMsg = "A reduction run - experiment %s, run %s, version %s - has failed:\n%s\n\n" % (reductionRun.experiment.reference_number, reductionRun.run_number, reductionRun.run_version, reductionRun.message)
        errorMsg += "The run will not retry automatically.\n" if not reductionRun.retry_when else "The run will automatically retry on %s.\n" % reductionRun.retry_when
        errorMsg += "Retry manually at %s%i/%i/ or on %sruns/failed/." % (BASE_URL, reductionRun.run_number, reductionRun.run_version, BASE_URL)
        
        emailContent = "From: %s\nTo: %s\nSubject:Autoreduction error\n\n%s" % (senderAddress, ", ".join(recipients), errorMsg)

        logger.info("Sending email: %s" % emailContent)
                       
        try:
            s = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            s.sendmail(senderAddress, recipients, emailContent)
            s.close()
        except Exception as e:
            logger.error("Failed to send emails %s" % emailContent)
            logger.error("Exception %s - %s" % (type(e).__name__, str(e)))
        
        
    def retryRun(self, reductionRun, retryIn):
        logger.info("RETRY RUN")
    
        if (reductionRun.cancel):
            logger.info("Cancelling run retry")
            return
            
        logger.info("Retrying run in %i seconds" % retryIn)
        
        new_job = ReductionRunUtils().createRetryRun(reductionRun, delay=retryIn)          
        try:
            MessagingUtils().send_pending(new_job, delay=retryIn*1000) # seconds to ms
        except Exception as e:
            new_job.delete()
            raise e
        

class Client(object):
    def __init__(self, brokers, user, password, topics=None, consumer_name='QueueProcessor', client_only=True, use_ssl=ACTIVEMQ['SSL']):
        self._brokers = brokers
        self._user = user
        self._password = password
        self._connection = None
        self._topics = topics
        self._consumer_name = consumer_name
        self._listener = None
        self._client_only = client_only
        self._use_ssl = use_ssl

    def set_listener(self, listener):
        self._listener = listener

    def get_connection(self, listener=None):
        if listener is None and not self._client_only:
            if self._listener is None:
                listener = Listener(self)
                self._listener = listener
            else:
                listener = self._listener

        logger.info("[%s] Connecting to %s" % (self._consumer_name, str(self._brokers)))

        connection = stomp.Connection(host_and_ports=self._brokers, use_ssl=self._use_ssl)
        if not self._client_only:
            connection.set_listener(self._consumer_name, listener)
        connection.start()
        connection.connect(self._user, self._password, wait=False)

        time.sleep(0.5)
        return connection

    def connect(self):
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
        
        for queue in self._topics:
            logger.info("[%s] Subscribing to %s" % (self._consumer_name, queue))
            self._connection.subscribe(destination=queue, id=1, ack='auto')

    def _disconnect(self):
        if self._connection is not None and self._connection.is_connected():
            self._connection.disconnect()
        self._connection = None
        logger.info("[%s] Disconnected" % (self._consumer_name))

    def stop(self):
        self._disconnect()
        if self._connection is not None:
            self._connection.stop()
        self._connection = None

    def send(self, destination, message, persistent='true', priority='4', delay=None):
        if self._connection is None or not self._connection.is_connected():
            self._disconnect()
            self._connection = self.get_connection()
            
        headers = {}
        if delay:
            headers['AMQ_SCHEDULED_DELAY'] = str(delay)
        self._connection.send(destination, message, persistent=persistent, priority=priority, headers=headers)
        logger.debug("[%s] send message to %s" % (self._consumer_name, destination))


def main():
    logger.info("MAIN")
    client = Client(ACTIVEMQ['broker'], ACTIVEMQ['username'], ACTIVEMQ['password'], ACTIVEMQ['topics'], 'Autoreduction_QueueProcessor', False, ACTIVEMQ['SSL'])
    client.connect()
    return client

if __name__ == '__main__':
    main()
