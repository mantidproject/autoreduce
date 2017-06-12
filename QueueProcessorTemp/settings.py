import logging
import os

MYSQL = {
    'HOST' : 'reducedev2.isis.cclrc.ac.uk',
    'USER' : 'autoreduce',
    'PASSWD' : 'activedev',
    'DB' : 'autoreduction'
}

# Logging
LOG_FILE = '/home/tip22963/queue_processor_daemon_log/autoreduction.log'
DEBUG = False

if DEBUG:
    LOG_LEVEL = 'DEBUG'
else:
    LOG_LEVEL = 'INFO'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.FileHandler',
            'filename': LOG_FILE,
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'queue_processor': {
            'handlers':['file'],
            'propagate': True,
            'level':LOG_LEVEL,
        },
        'app' : {
            'handlers':['file'],
            'propagate': True,
            'level':'DEBUG',
        },
    }
}

# ActiveMQ 
ACTIVEMQ = {
    'topics' : [
        '/queue/DataReady',
        '/queue/ReductionStarted',
        '/queue/ReductionComplete',
        '/queue/ReductionError'
        ],
    'username' : 'autoreduce',
    'password' : 'activedev',
    'broker' : [("autoreducedev2.isis.cclrc.ac.uk", 61613)],
    'SSL' : False
}

# ICAT 
ICAT = {
    'AUTH' : 'simple',
    'URL' : 'https://icatisis.esc.rl.ac.uk/ICATService/ICAT?wsdl',
    'USER' : 'autoreduce',
    'PASSWORD' : '2LzZWdds^QENuBw'
}

# Directory Locations
if os.name == 'nt':
    REDUCTION_DIRECTORY = r'\\isis\inst$\NDX%s\user\scripts\autoreduction' # %(instrument)
    ARCHIVE_DIRECTORY = r'\\isis\inst$\NDX%s\Instrument\data\cycle_%s\autoreduced\%s\%s' # %(instrument, cycle, experiment_number, run_number)
    
    TEST_REDUCTION_DIRECTORY = r'\\reducedev\isis\output\NDX%s\user\scripts\autoreduction'
    TEST_ARCHIVE_DIRECTORY = '\\isis\inst$\NDX%s\Instrument\data\cycle_%s\autoreduced\%s\%s'

else:
    REDUCTION_DIRECTORY = '/isis/NDX%s/user/scripts/autoreduction' # %(instrument)
    ARCHIVE_DIRECTORY = '/isis/NDX%s/Instrument/data/cycle_%s/autoreduced/%s/%s' # %(instrument, cycle, experiment_number, run_number)
    
    TEST_REDUCTION_DIRECTORY ='/reducedev/isis/output/NDX%s/user/scripts/autoreduction'
    TEST_ARCHIVE_DIRECTORY = '/isis/NDX%s/Instrument/data/cycle_%s/autoreduced/%s/%s'
