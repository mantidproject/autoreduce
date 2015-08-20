import logging
import logging.handlers

LOGGING_LEVEL = logging.INFO
LOGGING_LOC = '/var/log/autoreduction.log'

logger = logging.getLogger(__name__)
logger.setLevel(LOGGING_LEVEL)
handler = logging.handlers.RotatingFileHandler(LOGGING_LOC, maxBytes=104857600, backupCount=20)
handler.setLevel(LOGGING_LEVEL)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
# Quite the Stomp logs as they are quite chatty
logging.getLogger('stomp').setLevel(logging.INFO)