"""
This file contains celery tasks for sending email
"""
import logging

from boto.exception import NoAuthHandlerFound
from celery.exceptions import MaxRetriesExceededError
from celery.task import task  # pylint: disable=no-name-in-module, import-error
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core import mail
from django.core.exceptions import ObjectDoesNotExist
from edx_ace import ace
from edx_ace.errors import RecoverableChannelDeliveryError
from edx_ace.message import MessageType
from edx_ace.recipient import Recipient
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.lib.celery.task_utils import emulate_http_request

log = logging.getLogger('edx.celery.task')


class AccountActivation(MessageType):
    pass


@task(bind=True)
def send_activation_email(self, message, from_address=None):
    """
    Sending an activation email to the user.
    """
    site = Site.objects.filter(id=message.get('site_id'))

    msg = AccountActivation().personalize(
        recipient=Recipient(message.get('username'), message.get('dest_addr')),
        language=message.get('language'),
        user_context=message.get('user_context'),
    )

    max_retries = settings.RETRY_ACTIVATION_EMAIL_MAX_ATTEMPTS
    retries = self.request.retries
    dest_addr = msg.recipient.email_address

    try:
        user = User.objects.get(username=message.get('username'))
        with emulate_http_request(site=site[0], user=user):
            ace.send(msg)
            # Log that the Activation Email has been sent to user without an exception
            log.info("Activation Email has been sent to User {user_email}".format(
                user_email=dest_addr
            ))
    except (RecoverableChannelDeliveryError, ObjectDoesNotExist):
        log.info('Retrying sending email to user {dest_addr}, attempt # {attempt} of {max_attempts}'.format(
            dest_addr=dest_addr,
            attempt=retries,
            max_attempts=max_retries
        ))
        try:
            self.retry(countdown=settings.RETRY_ACTIVATION_EMAIL_TIMEOUT, max_retries=max_retries)
        except MaxRetriesExceededError:
            log.error(
                'Unable to send activation email to user from "%s" to "%s"',
                from_address,
                dest_addr,
                exc_info=True
            )
    except Exception:  # pylint: disable=bare-except
        log.exception(
            'Unable to send activation email to user from "%s" to "%s"',
            from_address,
            dest_addr,
            exc_info=True
        )
        raise Exception
