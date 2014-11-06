from autoreduce_webapp.uows_client import UOWSClient
from autoreduce_webapp.icat_communication import ICATCommunication
from django.conf import settings
from django.contrib.auth.models import User
from urllib2 import URLError
from settings import LOG_FILE, LOG_LEVEL, UOWS_URL
import logging
logging.basicConfig(filename=LOG_FILE,level=LOG_LEVEL)

class UOWSAuthenticationBackend(object):
    """
    Custom authentication for use with the User Office Web Service
    """
    def authenticate(self, token=None):
        """
        Checks that the given session ID (token) is still valid and returns an appropriate user object.
        If this is the first time a user has logged in a new user object is created.
        A users permissions (staff/superuser) is also set based on calls to ICAT.
        """
        with UOWSClient() as client:
            if client.check_session(token):
                person = client.get_person(token)
                try:
                    user = User.objects.get(username=person['usernumber'])
                except User.DoesNotExist:
                    user = User(username=person['usernumber'], password='get from uows', first_name=person['first_name'], last_name=person['last_name'], email=person['email'])

                try:
                    # Make sure user has correct permissions set. This will be checked upon each login
                    user.is_superuser = ICATCommunication().is_admin(int(person['usernumber']))
                    user.is_staff = (ICATCommunication().is_instrument_scientist(int(person['usernumber'])) or user.is_superuser)
                except URLError:
                    logging.error("Unable to connect to ICAT. Cannot update user's permission levels.")
                user.save()
                return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None