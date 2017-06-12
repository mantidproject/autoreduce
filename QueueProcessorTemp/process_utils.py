import os, io, logging, logging.config, chardet, imp, cgi, datetime, re
from settings import REDUCTION_DIRECTORY, LOGGING
from orm_mapping import *
from base import engine, session
from sqlalchemy.orm import sessionmaker

# Set up logging and attach the logging to the right part of the config.
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("queue_processor")

class DataTooLong(ValueError):
    pass

def log_error_and_notify(message):
    """
    Helper method to log an error and save a notifcation
    """
    logger.error(message)
    notification = Notification(is_active=True, is_staff_only=True, severity='e', message=message)
    session.add(notification)
    session.commit()


class ReductionRunUtils(object):
    def cancelRun(self, reductionRun):
        """
        Try to cancel the run given, or the run that was scheduled as the next retry of the run. When we cancel, we send a message to the backend queue processor, telling it to ignore this run if it arrives (most likely through a delayed message through ActiveMQ's scheduler). We also set statuses and error messages. If we can't do any of the above, we set the variable (retry_run.cancel) that tells the frontend to not schedule another retry if the next run fails.
        """

        def setCancelled(run):
            run.message = "Run cancelled by user"
            run.status = StatusUtils().get_error()
            run.finished = datetime.datetime.now()
            run.retry_when = None
            run.save()

        if reductionRun.status == StatusUtils().get_queued():  # this is the queued run, send the message to queueProcessor to cancel it
            MessagingUtils().send_cancel(reductionRun)
            setCancelled(reductionRun)

        # otherwise this run has already failed, and we're looking at a scheduled rerun of it
        elif not reductionRun.retry_run:  # we don't actually have a rerun, so just ensure the retry time is set to "Never" (None)
            reductionRun.retry_when = None

        elif reductionRun.retry_run.status == StatusUtils().get_queued():  # this run is being queued to retry, so send the message to queueProcessor to cancel it, and set it as cancelled
            MessagingUtils().send_cancel(reductionRun.retry_run)
            setCancelled(reductionRun.retry_run)

        elif reductionRun.retry_run.status == StatusUtils().get_processing():  # we have a run that's retrying, so just make sure it doesn't retry next time
            reductionRun.cancel = True
            reductionRun.retry_run.cancel = True

        else:  # the retry run already completed, so do nothing
            pass

        # save the run states we modified
        reductionRun.save()
        if reductionRun.retry_run:
            reductionRun.retry_run.save()

    def createRetryRun(self, reductionRun, script=None, variables=None, delay=0, username=None):
        """
        Create a run ready for re-running based on the run provided.
        If variables (RunVariable) are provided, copy them and associate them with the new one, otherwise use the previous run's.
        If a script (as a string) is supplied then use it, otherwise use the previous run's.
        """
        # find the previous run version, so we don't create a duplicate
        last_version = -1
        for run in ReductionRun.objects.filter(experiment=reductionRun.experiment, run_number=reductionRun.run_number):
            last_version = max(last_version, run.run_version)

        try:
            # get the script to use:
            script_text = script if script is not None else reductionRun.script

            # create the run object and save it
            new_job = ReductionRun(instrument=reductionRun.instrument
                                   , run_number=reductionRun.run_number
                                   , run_name=""
                                   , run_version=last_version + 1
                                   , experiment=reductionRun.experiment
                                   , started_by=username
                                   , status=StatusUtils().get_queued()
                                   , script=script_text
                                   )
            new_job.save()

            reductionRun.retry_run = new_job
            reductionRun.retry_when = datetime.datetime.now() + datetime.timedelta(
                seconds=delay if delay else 0)
            reductionRun.save()

            # copy the previous data locations
            for data_location in reductionRun.data_location.all():
                new_data_location = DataLocation(file_path=data_location.file_path, reduction_run=new_job)
                new_data_location.save()
                new_job.data_location.add(new_data_location)

            if variables is not None:
                # associate the variables with the new run
                for var in variables:
                    var.reduction_run = new_job
                    var.save()
            else:
                # provide variables if they aren't already
                InstrumentVariablesUtils().create_variables_for_run(new_job)

            return new_job

        except:
            new_job.delete()
            raise

    def get_script_and_arguments(self, reductionRun):
        """
        Fetch the reduction script from the given run and return it as a string, along with a dictionary of arguments.
        """
        script = reductionRun.script
        run_variables = (session.query(RunJoin).filter_by(reduction_run=reductionRun)).all()

        standard_vars, advanced_vars = {}, {}
        for variables in run_variables:
            value = VariableUtils().convert_variable_to_type(variables.value, variables.type)
            if variables.is_advanced:
                advanced_vars[variables.name] = value
            else:
                standard_vars[variables.name] = value

        arguments = {'standard_vars': standard_vars, 'advanced_vars': advanced_vars}

        return (script, arguments)

class InstrumentUtils(object):
    def get_instrument(self, instrument_name):
        """
        Helper method that will try to get an instrument matching the given name or create one if it doesn't yet exist
        """
        instrument = session.query(Instrument).filter_by(name=instrument_name).first()
        if instrument == None:
            instrument = Instrument(name=instrument_name, is_active=1, is_paused=0)
            session.add(instrument)
            session.commit()
            logger.warn("%s instrument was not found, created it." % instrument_name)
        return instrument


class VariableUtils(object):
    def derive_run_variable(self, instrument_var, reduction_run):
        return RunJoin(name=instrument_var.name,
                       value=instrument_var.value,
                       is_advanced=instrument_var.is_advanced,
                       type=instrument_var.type,
                       help_text=instrument_var.help_text,
                       reduction_run=reduction_run,
                       )

    def save_run_variables(self, instrument_vars, reduction_run):
        logger.info('Saving run variables for ' + str(reduction_run.run_number))
        runVariables = map(lambda iVar: self.derive_run_variable(iVar, reduction_run), instrument_vars)
        for run_variable in runVariables:
            session.add(run_variable)
        session.commit()
        return runVariables
    
    def copy_variable(self, variable):
        """ Return a temporary copy (unsaved) of the variable, which can be modified and then saved without modifying the original. """
        return InstrumentJoin (name = variable.name,
                               value = variable.value,
                               is_advanced = variable.is_advanced,
                               type = variable.type,
                               help_text = variable.help_text,
                               instrument = variable.instrument,
                               experiment_reference = variable.experiment_reference,
                               start_run = variable.start_run,
                               tracks_script = variable.tracks_script,
                               )
    
    def get_type_string(self, value):
        """
        Returns a textual representation of the type of the given value.
        The possible returned types are: text, number, list_text, list_number, boolean
        If the type isn't supported, it defaults to text.
        """
        var_type = type(value).__name__
        if var_type == 'str':
            return "text"
        if var_type == 'int' or var_type == 'float':
            return "number"
        if var_type == 'bool':
            return "boolean"
        if var_type == 'list':
            list_type = "number"
            for val in value:
                if type(val).__name__ == 'str':
                    list_type = "text"
            return "list_" + list_type
        return "text"

    def convert_variable_to_type(self, value, var_type):
        """
        Convert the given value a type matching that of var_type.
        Options for var_type: text, number, list_text, list_number, boolean
        If the var_type isn't recognised, the value is returned unchanged
        """
        if var_type == "text":
            return str(value)
        if var_type == "number":
            if not value or not re.match('(-)?[0-9]+', str(value)):
                return None
            if '.' in str(value):
                return float(value)
            else:
                return int(re.sub("[^0-9]+", "", str(value)))
        if var_type == "list_text":
            var_list = str(value).split(',')
            list_text = []
            for list_val in var_list:
                item = list_val.strip().strip("'")
                if item:
                    list_text.append(item)
            return list_text
        if var_type == "list_number":
            var_list = value.split(',')
            list_number = []
            for list_val in var_list:
                if list_val:
                    if '.' in str(list_val):
                        list_number.append(float(list_val))
                    else:
                        list_number.append(int(list_val))
            return list_number
        if var_type == "boolean":
            return value.lower() == 'true'
        return value


class InstrumentVariablesUtils():
    def show_variables_for_run(self, instrument_name, run_number=None):
        """
        Look for the applicable variables for the given run number. If none are set, return an empty list (or QuerySet)
        anyway.
        """
        instrument = InstrumentUtils().get_instrument(instrument_name)

        # If we haven't been given a run number, we should try to find it.
        if not run_number:
            applicable_variables = session.query(InstrumentVariable).filter_by(instrument=instrument)\
                                                                    .order_by('-start_run').all()
            if len(applicable_variables) != 0:
                variable_run_number = applicable_variables[0].start_run
        else:
            variable_run_number = run_number

        # Now use the InstrumentJoin class (which is a join of the InstrumentVariable and Variable tables) to make sure
        # we can make a copy of all the relevant variables with all of the right information.
        variables = (session.query(InstrumentJoin).filter_by(instrument=instrument,
                                                             start_run=variable_run_number)).all()

        # If we have found some variables then we want to use them by first making copies of them and sending them back
        # to be used. This means we don't alter the previous set of variables. If we haven't found any variables, just
        # return an empty list.
        if len(variables) != 0:
            logger.info(len(variables))
            logger.info(variables[0].name)
            self._update_variables(variables)
            for variable in variables:
                logger.info(variable.name)
            new_variables = []
            for variable in variables:
                new_variables.append(VariableUtils().copy_variable(variable))
            return new_variables
        else:
            return []
    
    def _create_variables(self, instrument, script, variable_dict, is_advanced):
        variables = []
        for key, value in variable_dict.iteritems():
            str_value = str(value).replace('[','').replace(']','')
            logger.info(str_value)
            max_value = Variable.value.property.columns[0].type.length
            if len(str_value) > max_value:
                raise DataTooLong

            variable = InstrumentVariable( instrument=instrument
                                         , name=key
                                         , value=str_value
                                         , is_advanced=is_advanced
                                         , type=VariableUtils().get_type_string(value)
                                         , start_run = 0
                                         , help_text=self._get_help_text('standard_vars', key, instrument.name, script)
                                         )

            session.add(variable)
            session.add(instrument_variable)
            session.commit()
            
            variables.append(variable)
        return variables
    
    def get_default_variables(self, instrument_name, reduce_script=None):
        """
        Creates and returns a list of variables from the reduction script on disk for the instrument.
        If reduce_script is supplied, return variables using that script instead of the one on disk.
        """
        if not reduce_script:
            reduce_script = self._load_reduction_vars_script(instrument_name)

        reduce_vars_module = self._read_script(reduce_script, os.path.join(self._reduction_script_location(instrument_name), 'reduce_vars.py'))
        if not reduce_vars_module:
            return []
        
        instrument = InstrumentUtils().get_instrument(instrument_name)
        variables = []
        if 'standard_vars' in dir(reduce_vars_module):
            variables.extend(self._create_variables(instrument, reduce_vars_module, reduce_vars_module.standard_vars, False))
        if 'advanced_vars' in dir(reduce_vars_module):
            variables.extend(self._create_variables(instrument, reduce_vars_module, reduce_vars_module.advanced_vars, True))
            
        for var in variables:
            var.tracks_script = True

        applicable_variables = session.query(InstrumentVariable).filter_by(instrument=instrument) \
            .order_by('-start_run').all()
        variable_run_number = applicable_variables[0].start_run

        # Now use the InstrumentJoin class (which is a join of the InstrumentVariable and Variable tables) to make sure
        # we can make a copy of all the relevant variables with all of the right information.
        variables = (session.query(InstrumentJoin).filter_by(instrument=instrument,
                                                             start_run=variable_run_number)).all()
        
        return variables
    
    def _update_variables(self, variables, save=True):
        """ 
        Updates all variables with tracks_script to their value in the script, and append any new ones. 
        This assumes that the variables all belong to the same instrument, and that the list supplied is complete.
        If no variables have tracks_script set, we won't do anything at all.
        variables should be a list; it needs to be mutable so that this function can add/remove variables.
        If the 'save' option is true, it will save/delete the variables from the database as required.
        """
        if not any([hasattr(var, "tracks_script") and var.tracks_script for var in variables]):
            return
        
        # New variable set from the script
        defaults = self.get_default_variables(variables[0].instrument.name) if variables else []

        # Update the existing variables
        def updateVariable(oldVar):
            oldVar.keep = True
            matchingVars = filter(lambda var: var.name == oldVar.name, defaults) # Find the new variable from the script.
            if matchingVars and oldVar.tracks_script: # Check whether we should and can update the old one.
                newVar = matchingVars[0]
                map(lambda name: setattr(oldVar, name, getattr(newVar, name)),
                    ["value", "type", "is_advanced", "help_text"]) # Copy the new one's important attributes onto the old variable.
                if save: 
                    session.add(oldVar)
                    session.commit()
            elif not matchingVars:
                # Or remove the variable if it doesn't exist any more.
                if save: 
                    session.delete(oldVar)
                    session.commit()
                oldVar.keep = False
        map(updateVariable, variables)
        variables[:] = [var for var in variables if var.keep]

        # Add any new ones
        current_names = [var.name for var in variables]
        new_vars = [var for var in defaults if var.name not in current_names]

        def copyMetadata(newVar):
            sourceVar = variables[0]
            if isinstance(sourceVar, InstrumentVariable):
                # Copy the source variable's metadata to the new one.
                map(lambda name: setattr(newVar, name, getattr(sourceVar, name)), ["instrument", "experiment_reference", "start_run"])
            elif isinstance(sourceVar, RunVariable):
                # Create a run variable.
                VariableUtils().derive_run_variable(newVar, sourceVar.reduction_run)
            else: return
            session.add(newVar)
            session.commit()
        map(copyMetadata, new_vars)
        variables += list(new_vars)


    def _reduction_script_location(self, instrument_name):
        return REDUCTION_DIRECTORY % instrument_name
    
    def _load_reduction_script(self, instrument_name):
        return self._load_script(os.path.join(self._reduction_script_location(instrument_name), 'reduce.py'))
        
    def _load_reduction_vars_script(self, instrument_name):
        return self._load_script(os.path.join(self._reduction_script_location(instrument_name), 'reduce_vars.py'))
        
    def _read_script(self, script_text, script_path):
        """ Takes a python script as a text string, and returns it loaded as a module. Failure will return None, and notify. """
        if not script_text or not script_path:
            return None

        module_name = os.path.basename(script_path).split(".")[0] # file name without extension
        script_module = imp.new_module(module_name)
        try:
            exec script_text in script_module.__dict__
            return script_module
        except ImportError as e:
            log_error_and_notify("Unable to load reduction script %s due to missing import. (%s)" % (script_path, e.message))
            return None
        except SyntaxError:
            log_error_and_notify("Syntax error in reduction script %s" % script_path)
            return None
    
    def _create_variables(self, instrument, script, variable_dict, is_advanced):
        variables = []
        for key, value in variable_dict.iteritems():
            str_value = str(value).replace('[','').replace(']','')
            max_value = Variable.value.property.columns[0].type.length
            if len(str_value) > 300:
                raise DataTooLong
            
            variable = Variable(name=key,
                                value=str_value,
                                type=VariableUtils().get_type_string(value),
                                is_advanced=is_advanced,
                                help_text=self._get_help_text('standard_vars', key, instrument.name, script)
                               )
            
            instrument_variable = InstrumentVariable(start_run=0,
                                                     instrument=instrument,
                                                     variable=variable,
                                                     tracks_script=1
                                                    )
            
            session.add(variable)
            session.add(instrument_variable)
            session.commit()

            variables.append(instrument_variable)
        return variables

    def get_current_script_text(self, instrument_name):
        """
        Fetches the reduction script and variables script for the given 
        instrument, and returns each as a string.
        """
        script_text = self._load_reduction_script(instrument_name)
        script_vars_text = self._load_reduction_vars_script(instrument_name)
        return (script_text, script_vars_text)
    
    def _load_script(self, path):
        """
        First detect the file encoding using chardet.
        Then load the relevant reduction script and return back the text of the script.
        If the script cannot be loaded, None is returned.
        """
        try:
            # Read raw bytes and determine encoding
            f_raw = io.open(path, 'rb')
            encoding = chardet.detect(f_raw.read(32))["encoding"]
            
            # Read the file in decoded; io is used for the encoding kwarg
            f = io.open(path, 'r', encoding=encoding)
            script_text = f.read()
            return script_text
        except Exception as e:
            log_error_and_notify("Unable to load reduction script %s - %s" % (path, e))
            return None
        
    def create_variables_for_run(self, reduction_run):
        """
        Finds the appropriate InstrumentVariables for the given reduction run, and creates RunVariables from them.
        If the run is a re-run, use the previous run's variables.
        If instrument variables set for the run's experiment are found, they're used.
        Otherwise if variables set for the run's run number exist, they'll be used.
        If not, the instrument's default variables will be used.
        """
        instrument_name = reduction_run.instrument.name
        
        variables = []

        # TODO: Probably need to remove this as I don't think we ever set the experiment ref anyway. Look into it.
        if not variables:
            logger.info('Finding variables from experiment')
            # No previous run versions. Find the instrument variables we want to use.
            variables = self.show_variables_for_experiment(instrument_name, reduction_run.experiment.reference_number)

        if not variables:
            logger.info('Finding variables from run number')
            # No experiment-specific variables, so let's look for variables set by run number.
            variables = self.show_variables_for_run(instrument_name, reduction_run.run_number)

        if not variables:
            logger.info('Using default variables')
            # No variables are set, so we'll use the defaults, and set them them while we're at it.
            variables = self.get_default_variables(instrument_name)
            logger.info('Setting the variables for the run')
            self.set_variables_for_runs(instrument_name, variables, reduction_run.run_number)

        logger.info('Saving the found variables')
        # Create run variables from these instrument variables, and return them.
        return VariableUtils().save_run_variables(variables, reduction_run)
    
    def set_variables_for_runs(self, instrument_name, variables, start_run=0, end_run=None):
        """
        Given a list of variables, we set them to be the variables used for subsequent runs in the given run range.
        If end_run is not supplied, these variables will be ongoing indefinitely.
        If start_run is not supplied, these variables will be set for all run numbers going backwards.
        """
        instrument = InstrumentUtils().get_instrument(instrument_name)
        # In this case we need to make sure that the variables we set will be the only ones used for the range given.
        # If there are variables which apply after the given range ends, we want to create/modify a set to have a start_run after this end_run, with the right values.
        # First, find all variables that are in the range.
        applicable_variables = session.query(InstrumentVariable).filter_by(instrument = instrument, start_run = start_run).all()
        final_variables = []
        if end_run:
            applicable_variables = applicable_variables.filter(start_run__lte = end_run)
            after_variables = InstrumentVariable.objects.filter(instrument = instrument, start_run = end_run + 1).order_by('start_run')
            previous_variables = InstrumentVariable.objects.filter(instrument = instrument, start_run__lt = start_run)

            if applicable_variables and not after_variables:
                # The last set of applicable variables extends outside our range.
                final_start = applicable_variables.order_by('-start_run').first().start_run # Find the last set.
                final_variables = list(applicable_variables.filter(start_run = final_start))
                applicable_variables = applicable_variables.exclude(start_run = final_start) # Don't delete the final set.
                
            elif not applicable_variables and not after_variables and previous_variables:
                # There is a previous set that applies but doesn't start or end in the range.
                final_start = previous_variables.order_by('-start_run').first().start_run # Find the last set.
                final_variables = list(previous_variables.filter(start_run = final_start)) # Set them to apply after our variables.
                [VariableUtils().copy_variable(var).save() for var in final_variables] # Also copy them to apply before our variables.
                
            elif not applicable_variables and not after_variables and not previous_variables:
                # There are instrument defaults which apply after our range.
                final_variables = self.get_default_variables(instrument_name)
                
        # Delete all currently saved variables that apply to the range.
        map(lambda var: var.delete(), applicable_variables)
        
        # Modify the range of the final set to after the specified range, if there is one.
        for var in final_variables:
            var.start_run = end_run + 1
            session.add(var)
            session.commit()

        # Then save the new ones.
        for var in variables:
            var.start_run = start_run
            session.add(var)
            session.commit()

    def show_variables_for_experiment(self, instrument_name, experiment_reference):
        """ Look for currently set variables for the experiment. If none are set, return an empty list (or QuerySet) anyway. """
        instrument = InstrumentUtils().get_instrument(instrument_name)
        vars = session.query(InstrumentVariable).filter_by(instrument=instrument, experiment_reference=experiment_reference).all()
        self._update_variables(vars)
        return [VariableUtils().copy_variable(var) for var in vars]
            
    def _get_help_text(self, dictionary, key, instrument_name, reduce_script=None):
        if not dictionary or not key:
            return ""
        if not reduce_script:
            reduce_script = self._load_reduction_vars_script(instrument_name)
        if 'variable_help' in dir(reduce_script):
            if dictionary in reduce_script.variable_help:
                if key in reduce_script.variable_help[dictionary]:
                    return self._replace_special_chars(reduce_script.variable_help[dictionary][key])
        return ""
    
    def _replace_special_chars(self, help_text):
        help_text = cgi.escape(help_text)  # Remove any HTML already in the help string
        help_text = help_text.replace('\n', '<br>').replace('\t', '&nbsp;&nbsp;&nbsp;&nbsp;')
        return help_text

class MessagingUtils(object):
    def send_pending(self, reduction_run, delay=None):
        """ Sends a message to the queue with the details of the job to run. """
        data_dict = self._make_pending_msg(reduction_run)
        self._send_pending_msg(data_dict, delay)

    def send_cancel(self, reduction_run):
        """ Sends a message to the queue telling it to cancel any reruns of the job. """
        data_dict = self._make_pending_msg(reduction_run)
        data_dict["cancel"] = True
        self._send_pending_msg(data_dict)

    def _make_pending_msg(self, reduction_run):
        """ Creates a dict message from the given run, ready to be sent to ReductionPending. """
        script, arguments = ReductionRunUtils().get_script_and_arguments(reduction_run)

        data_path = ''
        # Currently only support single location
        data_location = reduction_run.data_location.first()
        if data_location:
            data_path = data_location.file_path
        else:
            raise Exception("No data path found for reduction run")

        data_dict = {
            'run_number':reduction_run.run_number,
            'instrument':reduction_run.instrument.name,
            'rb_number':str(reduction_run.experiment.reference_number),
            'data':data_path,
            'reduction_script':script,
            'reduction_arguments':arguments,
            'run_version':reduction_run.run_version,
            'facility':FACILITY,
            'message':'',
        }

        return data_dict

    def _send_pending_msg(self, data_dict, delay=None):
        """ Sends data_dict to ReductionPending (with the specified delay) """
        from queue_processor import Client as ActiveMQClient # to prevent circular dependencies

        message_client = ActiveMQClient(ACTIVEMQ['broker'], ACTIVEMQ['username'], ACTIVEMQ['password'], ACTIVEMQ['topics'], 'Webapp_QueueProcessor', False, ACTIVEMQ['SSL'])
        message_client.connect()
        message_client.send('/queue/ReductionPending', json.dumps(data_dict), priority='0', delay=delay)
        message_client.stop()


class StatusUtils(object):
    def _get_status(self, status_value):
        """
        Helper method that will try to get a status matching the given name or create one if it doesn't yet exist
        """
        status = session.query(Status).filter_by(value=status_value)[0]
        if status is None:
            new_status = Status(value=status_value)
            session.add(new_status)
            session.commit()
            status = session.query(InstrumentVariable).filter_by(value=status_value)[0]
            logger.warn("%s status was not found, created it." % status_value)
        return status

    def get_error(self):
        return self._get_status("Error")

    def get_completed(self):
        return self._get_status("Completed")

    def get_processing(self):
        return self._get_status("Processing")

    def get_queued(self):
        return self._get_status("Queued")

    def get_skipped(self):
        return self._get_status("Skipped")