import os, io, logging, logging.config, chardet
from settings import REDUCTION_DIRECTORY, LOGGING
from orm_mapping import *
from base import engine
from sqlalchemy.orm import sessionmaker

# Set up logging and attach the logging to the right part of the config.
logging.config.dictConfig(LOGGING)
logger = logging.getLogger("queue_processor")

Session = sessionmaker(bind=engine)
session = Session()

def log_error_and_notify(message):
	"""
	Helper method to log an error and save a notifcation
	"""
	logger.error(message)
	notification = Notification(is_active=True, is_staff_only=True, severity='e', message=message)
	session.add(notification)
	session.commit()

class VariableUtils(object):
	def save_run_variables(self, instrument_vars, reduction_run):
		runVariables = map(lambda iVar: self.derive_run_variable(iVar, reduction_run), instrument_vars)
		map(lambda rVar: rVar.save(), runVariables)
		return runVariables

class InstrumentVariablesUtils():
	def _reduction_script_location(self, instrument_name):
		return REDUCTION_DIRECTORY % instrument_name
	
	def _load_reduction_script(self, instrument_name):
		return self._load_script(os.path.join(self._reduction_script_location(instrument_name), 'reduce.py'))
		
	def _load_reduction_vars_script(self, instrument_name):
		return self._load_script(os.path.join(self._reduction_script_location(instrument_name), 'reduce_vars.py'))

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
		Finds the appropriate `InstrumentVariable`s for the given reduction run, and creates `RunVariable`s from them.
		If the run is a re-run, use the previous run's variables.
		If instrument variables set for the run's experiment are found, they're used.
		Otherwise if variables set for the run's run number exist, they'll be used.
		If not, the instrument's default variables will be.
		"""
		instrument_name = reduction_run.instrument.name
		variables = []
		
		if not variables:
			# No previous run versions. Find the instrument variables we want to use.
			variables = self.show_variables_for_experiment(instrument_name, reduction_run.experiment.reference_number)

		if not variables:
			# No experiment-specific variables, so let's look for variables set by run number.
			variables = self.show_variables_for_run(instrument_name, reduction_run.run_number)

		if not variables:
			# No variables are set, so we'll use the defaults, and set them them while we're at it.
			variables = self.get_default_variables(instrument_name)
			self.set_variables_for_runs(instrument_name, variables, reduction_run.run_number)

		# Create run variables from these instrument variables, and return them.
		return VariableUtils().save_run_variables(variables, reduction_run)