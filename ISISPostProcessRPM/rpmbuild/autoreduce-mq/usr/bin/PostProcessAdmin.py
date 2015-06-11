#!/usr/bin/env python
"""
Post Process Administrator. It kicks off cataloging and reduction jobs.
"""
import logging, json, socket, os, sys, subprocess, time, shutil, imp, stomp, re
import logging.handlers
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler('/var/log/autoreduction.log', maxBytes=104857600, backupCount=20)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# Quite the Stomp logs as they are quite chatty
logging.getLogger('stomp').setLevel(logging.INFO)

REDUCTION_DIRECTORY = '/isis/NDX%s/user/scripts/autoreduction' # %(instrument)
#ARCHIVE_DIRECTORY = '/isis/NDX%s/Instrument/data/cycle_%s/autoreduced/%s/%s' # %(instrument, cycle, experiment_number, run_number)
#Archive not being used for any instruments currently.
CEPH_DIRECTORY = '/instrument/%s/CYCLE20%s/RB%s/autoreduced/%s' # %(instrument, cycle, experiment_number, run_number)
TEMP_ROOT_DIRECTORY = '/autoreducetmp'

def copytree(src, dst):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d)
        else:
            if not os.path.exists(d) or os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)

def linux_to_windows_path(path):
    path = path.replace('/', '\\')
    # '/isis/' maps to '\\isis\inst$\'
    path = path.replace('\\isis\\', '\\\\isis\\inst$\\')
    return path

def windows_to_linux_path(path):
    # '\\isis\inst$\' maps to '/isis/'
    path = path.replace('\\\\isis\\inst$\\', '/isis/')
    path = path.replace('\\\\autoreduce\\data\\', TEMP_ROOT_DIRECTORY+'/data/')
    path = path.replace('\\', '/')
    return path

class PostProcessAdmin:
    def __init__(self, data, conf, connection):

        logger.debug("json data: " + str(data))
        data["information"] = socket.gethostname()
        self.data = data
        self.conf = conf
        self.client = connection

        try:
            if data.has_key('data'):
                self.data_file = windows_to_linux_path(str(data['data']))
                logger.debug("data_file: %s" % self.data_file)
            else:
                raise ValueError("data is missing")

            if data.has_key('facility'):
                self.facility = str(data['facility']).upper()
                logger.debug("facility: %s" % self.facility)
            else: 
                raise ValueError("facility is missing")

            if data.has_key('instrument'):
                self.instrument = str(data['instrument']).upper()
                logger.debug("instrument: %s" % self.instrument)
            else:
                raise ValueError("instrument is missing")

            if data.has_key('rb_number'):
                self.proposal = str(data['rb_number']).upper()
                logger.debug("rb_number: %s" % self.proposal)
            else:
                raise ValueError("rb_number is missing")
                
            if data.has_key('run_number'):
                self.run_number = str(data['run_number'])
                logger.debug("run_number: %s" % self.run_number)
            else:
                raise ValueError("run_number is missing")
                
            if data.has_key('reduction_script'):
                self.reduction_script = windows_to_linux_path(str(data['reduction_script']))
                logger.debug("reduction_script: %s" % str(self.reduction_script))
            else:
                raise ValueError("reduction_script is missing")
                
            if data.has_key('reduction_arguments'):
                self.reduction_arguments = data['reduction_arguments']
                logger.debug("reduction_arguments: %s" % self.reduction_arguments)
            else:
                raise ValueError("reduction_arguments is missing")

        except ValueError:
            logger.info('JSON data error', exc_info=True)
            raise

    def parse_input_variable(self, default, value):
        varType = type(default)
        if varType.__name__ == "str":
            return str(value)
        if varType.__name__ == "int":
            return int(value)
        if varType.__name__ == "list":
            return value.split(',')
        if varType.__name__ == "bool":
            return (value.lower() is 'true')
        if varType.__name__ == "float":
            return float(value)

    def replace_variables(self, reduce_script):
        if hasattr(reduce_script, 'web_var'):
            if hasattr(reduce_script.web_var, 'standard_vars'):
                for key in reduce_script.web_var.standard_vars:
                    if 'standard_vars' in self.reduction_arguments and key in self.reduction_arguments['standard_vars']:
                        if type(self.reduction_arguments['standard_vars'][key]).__name__ == 'unicode':
                            self.reduction_arguments['standard_vars'][key] = self.reduction_arguments['standard_vars'][key].encode('ascii','ignore')
                        reduce_script.web_var.standard_vars[key] = self.reduction_arguments['standard_vars'][key]
            if hasattr(reduce_script.web_var, 'advanced_vars'):
                for key in reduce_script.web_var.advanced_vars:
                    if 'advanced_vars' in self.reduction_arguments and key in self.reduction_arguments['advanced_vars']:
                        if type(self.reduction_arguments['advanced_vars'][key]).__name__ == 'unicode':
                            self.reduction_arguments['advanced_vars'][key] = self.reduction_arguments['advanced_vars'][key].encode('ascii','ignore')
                        reduce_script.web_var.advanced_vars[key] = self.reduction_arguments['advanced_vars'][key]
        return reduce_script

    def reduce(self):
        print "\n> In reduce()\n"
        try:         
            print "\nCalling: " + self.conf['reduction_started'] + "\n" + json.dumps(self.data) + "\n"
            logger.debug("Calling: " + self.conf['reduction_started'] + "\n" + json.dumps(self.data))
            self.client.send(self.conf['reduction_started'], json.dumps(self.data))

            # specify instrument directory  
            cycle = re.sub('[_]','',(re.match('.*cycle_(\d\d_\d).*', self.data['data'].lower()).group(1)))
            instrument_dir = CEPH_DIRECTORY % (self.instrument.upper(), cycle, self.data['rb_number'], self.data['run_number'])
	    
            # specify script to run and directory
            if os.path.exists(os.path.join(self.reduction_script, "reduce.py")) == False:
                self.data['message'] = "Reduce script doesn't exist within %s" % self.reduction_script
                logger.info("Reduction script not found within %s" % self.reduction_script)
                self.client.send(self.conf['reduction_error'] , json.dumps(self.data))  
                print "\nCalling: "+self.conf['reduction_error'] + "\n" + json.dumps(self.data) + "\n"
                logger.debug("Calling: "+self.conf['reduction_error'] + "\n" + json.dumps(self.data))
                return
            
            # specify directory where autoreduction output goes
            run_output_dir = TEMP_ROOT_DIRECTORY + instrument_dir[:instrument_dir.find('/'+ str(self.data['run_number']))+1]
            reduce_result_dir = TEMP_ROOT_DIRECTORY + instrument_dir + "/results/"
            reduce_result_dir_tail_length = len("/results")
            if not os.path.isdir(reduce_result_dir):
                os.makedirs(reduce_result_dir)

            log_dir = reduce_result_dir + "reduction_log/"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            self.data['reduction_data'] = []
            if "message" not in self.data:
                self.data["message"] = ""

            # Load reduction script
            sys.path.append(self.reduction_script)
            reduce_script = imp.load_source('reducescript', os.path.join(self.reduction_script, "reduce.py"))
            out_log = os.path.join(log_dir, self.data['rb_number'] + ".log")
            out_err = os.path.join(reduce_result_dir, self.data['rb_number'] + ".err")

            logger.info("----------------")
            logger.info("Reduction script: %s" % self.reduction_script)
            logger.info("Result dir: %s" % reduce_result_dir)
            logger.info("Run Output dir: %s" % run_output_dir)
            logger.info("Log dir: %s" % log_dir)
            logger.info("Out log: %s" % out_log)
            logger.info("----------------")

            logger.info("Reduction subprocess started.")
            logFile=open(out_log, "w")
            errFile=open(out_err, "w")
            # Set the output to be the logfile
            sys.stdout = logFile
            sys.stderr = errFile
            reduce_script = self.replace_variables(reduce_script)
            try:
                out_directories = reduce_script.main(input_file=str(self.data_file), output_dir=str(reduce_result_dir))
            except Exception as e:
                self.copy_temp_directory(reduce_result_dir, reduce_result_dir_tail_length)
                raise
            finally:
                # Reset outputs back to default
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                logFile.close()
                errFile.close()

            logger.info("Reduction subprocess completed.")
            logger.info("Additional save directories: %s" % out_directories)

            # If the reduce script specified some additional save directories, copy to there first
            if out_directories:
                if type(out_directories) is str and os.access(out_directories, os.R_OK):
                    self.data['reduction_data'].append(linux_to_windows_path(out_directories))
                    if not os.path.exists(out_directories):
                        os.makedirs(out_directories)
                    try:
                        copytree(run_output_dir[:-1], out_directories)
                    except Exception, e:
                        self.log_and_message("Unable to copy %s to %s - %s" % (run_output_dir[:-1], out_directories, e))
                elif type(out_directories) is list:
                    for out_dir in out_directories:
                        self.data['reduction_data'].append(linux_to_windows_path(out_dir))
                        if not os.path.exists(out_dir):
                            os.makedirs(out_dir)
                        if type(out_dir) is str and os.access(out_dir, os.R_OK):
                            try:
                                copytree(run_output_dir[:-1], out_dir)
                            except Exception, e:
                                self.log_and_message("Unable to copy %s to %s - %s" % (run_output_dir[:-1], out_dir, e))
                        else:
                            logger.info("Unable to access directory: %s" % out_dir)

            self.copy_temp_directory(reduce_result_dir, reduce_result_dir_tail_length)

            if os.stat(out_err).st_size == 0:
                os.remove(out_err)
                self.client.send(self.conf['reduction_complete'] , json.dumps(self.data))
                print "\nCalling: "+self.conf['reduction_complete'] + "\n" + json.dumps(self.data) + "\n"
            else:
                maxLineLength=80
                fp=file(out_err, "r")
                fp.seek(-maxLineLength-1, 2) # 2 means "from the end of the file"
                lastLine = fp.readlines()[-1]
                errMsg = lastLine.strip() + ", see reduction_log/" + os.path.basename(out_log) + " or " + os.path.basename(out_err) + " for details."
                self.data["message"] = "REDUCTION: %s" % errMsg
                self.client.send(self.conf['reduction_error'], json.dumps(self.data))
                logger.info("Called "+self.conf['reduction_error'] + " --- " + json.dumps(self.data))

            logger.info("Reduction job complete")
        except Exception, e:
            try:
                self.data["message"] = "REDUCTION Error: %s " % e
                logger.exception("Called "+self.conf['reduction_error']  + "\nException: " + str(e) + "\nJSON: " + json.dumps(self.data))
                self.client.send(self.conf['reduction_error'] , json.dumps(self.data))
            except BaseException, e:
                print "\nFailed to send to queue!\n%s\n%s" % (e, repr(e))
                logger.info("Failed to send to queue! - %s - %s" % (e, repr(e)))

    def copy_temp_directory(self, reduce_result_dir, reduce_result_dir_tail_length):
        """ Method that copies the temporary files held in results_directory to CEPH/archive, replacing old data if it
        exists"""
        copy_destination = reduce_result_dir[len(TEMP_ROOT_DIRECTORY):-reduce_result_dir_tail_length]
        if os.path.isdir(copy_destination):
            try:
                shutil.rmtree(copy_destination, ignore_errors=True)
            except Exception, e:
                logger.info("Unable to remove existing directory %s - %s" % (copy_destination, e))
        try:
            os.makedirs(copy_destination)
        except Exception, e:
            self.log_and_message("Unable to create %s - %s. " % (copy_destination, e))

        # [4,-8] is used to remove the prepending '/tmp' and the trailing 'results/' from the destination
        self.data['reduction_data'].append(linux_to_windows_path(copy_destination))
        logger.info("Moving %s to %s" % (reduce_result_dir[:-1], copy_destination))
        try:
            shutil.copytree(reduce_result_dir[:-1], reduce_result_dir[len(TEMP_ROOT_DIRECTORY):])
        except Exception, e:
            self.log_and_message("Unable to copy to %s - %s" % (reduce_result_dir[len(TEMP_ROOT_DIRECTORY):], e))

        # Remove temporary working directory
        try:
            shutil.rmtree(reduce_result_dir[:-reduce_result_dir_tail_length], ignore_errors=True)
        except Exception, e:
            logger.info("Unable to remove temporary directory %s - %s" % reduce_result_dir)

    def log_and_message(self, message):
        """Helper function to add text to the outgoing activemq message and to the info logs """
        logger.info(message)
        self.data["message"] += message

if __name__ == "__main__":

    print "\n> In PostProcessAdmin.py\n"

    try:
        conf = json.load(open('/etc/autoreduce/post_process_consumer.conf'))

        brokers = []
        brokers.append((conf['brokers'].split(':')[0],int(conf['brokers'].split(':')[1])))
        connection = stomp.Connection(host_and_ports=brokers, use_ssl=True, ssl_version=3 )
        connection.start()
        connection.connect(conf['amq_user'], conf['amq_pwd'], wait=False, header={'activemq.prefetchSize': '1',})

        destination, message = sys.argv[1:3]
        print("destination: " + destination)
        print("message: " + message)
        data = json.loads(message)
        
        try:  
            pp = PostProcessAdmin(data, conf, connection)
            if destination == '/queue/ReductionPending':
                pp.reduce()

        except ValueError as e:
            data["error"] = str(e)
            logger.info("JSON data error: " + json.dumps(data))

            connection.send(conf['postprocess_error'], json.dumps(data))
            print("Called " + conf['postprocess_error'] + "----" + json.dumps(data))
            raise
        
        except:
            raise
        
    except Error as er:
	logger.info("Something went wrong: " + str(er))
        sys.exit()


