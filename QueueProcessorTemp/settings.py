import logging
import os

MYSQL = {
    'HOST' : 'reducedev2.isis.cclrc.ac.uk',
    'USER' : 'autoreduce',
    'PASSWD' : 'activedev',
    'DB' : 'autoreduction'
}

# Logging
LOG_FILE = '/home/tip22963/autoreduction.log'
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
