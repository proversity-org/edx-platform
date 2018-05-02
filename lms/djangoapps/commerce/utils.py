"""Utilities to assist with commerce tasks."""
import json
import logging
from urllib import urlencode
from urlparse import urljoin

import requests
import waffle
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from openedx.core.djangoapps.commerce.utils import ecommerce_api_client, is_commerce_service_configured
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.theming import helpers as theming_helpers
from student.models import CourseEnrollment
from .models import CommerceConfiguration

log = logging.getLogger(__name__)


def is_account_activation_requirement_disabled():
    """
    Checks to see if the django-waffle switch for disabling the account activation requirement is active

    Returns:
        Boolean value representing switch status
    """
    switch_name = configuration_helpers.get_value(
        'DISABLE_ACCOUNT_ACTIVATION_REQUIREMENT_SWITCH',
        settings.DISABLE_ACCOUNT_ACTIVATION_REQUIREMENT_SWITCH
    )
    return waffle.switch_is_active(switch_name)


class EcommerceService(object):
    """ Helper class for ecommerce service integration. """
    def __init__(self):
        self.config = CommerceConfiguration.current()

    @property
    def ecommerce_url_root(self):
        """ Retrieve Ecommerce service public url root. """
        return configuration_helpers.get_value('ECOMMERCE_PUBLIC_URL_ROOT', settings.ECOMMERCE_PUBLIC_URL_ROOT)

    def get_absolute_ecommerce_url(self, ecommerce_page_url):
        """ Return the absolute URL to the ecommerce page.

        Args:
            ecommerce_page_url (str): Relative path to the ecommerce page.

        Returns:
            Absolute path to the ecommerce page.
        """
        return urljoin(self.ecommerce_url_root, ecommerce_page_url)

    def get_receipt_page_url(self, order_number):
        """
        Gets the URL for the Order Receipt page hosted by the ecommerce service.

        Args:
            order_number (str): Order number.

        Returns:
            Receipt page for the specified Order.
        """

        return self.get_absolute_ecommerce_url(CommerceConfiguration.DEFAULT_RECEIPT_PAGE_URL + order_number)

    def is_enabled(self, user):
        """
        Determines the availability of the EcommerceService based on user activation and service configuration.
        Note: If the user is anonymous we bypass the user activation gate and only look at the service config.

        Returns:
            Boolean
        """
        user_is_active = user.is_active or is_account_activation_requirement_disabled()
        allow_user = user_is_active or user.is_anonymous
        return allow_user and self.config.checkout_on_ecommerce_service

    def payment_page_url(self):
        """ Return the URL for the checkout page.

        Example:
            http://localhost:8002/basket/single_item/
        """
        return self.get_absolute_ecommerce_url(self.config.single_course_checkout_page)

    def get_checkout_page_url(self, *skus):
        """ Construct the URL to the ecommerce checkout page and include products.

        Args:
            skus (list): List of SKUs associated with products to be added to basket

        Returns:
            Absolute path to the ecommerce checkout page showing basket that contains specified products.

        Example:
            http://localhost:8002/basket/add/?sku=5H3HG5&sku=57FHHD
        """
        return '{checkout_page_path}?{skus}'.format(
            checkout_page_path=self.get_absolute_ecommerce_url(self.config.MULTIPLE_ITEMS_BASKET_PAGE_URL),
            skus=urlencode({'sku': skus}, doseq=True),
        )

    def upgrade_url(self, user, course_key):
        """
        Returns the URL for the user to upgrade, or None if not applicable.
        """
        enrollment = CourseEnrollment.get_enrollment(user, course_key)
        verified_mode = enrollment.verified_mode if enrollment else None
        if verified_mode:
            if self.is_enabled(user):
                return self.get_checkout_page_url(verified_mode.sku)
            else:
                return reverse('verify_student_upgrade_and_verify', args=(course_key,))
        return None


def refund_entitlement(course_entitlement):
    """
    Attempt a refund of a course entitlement. Verify the User before calling this refund method

    Returns:
        bool: True if the Refund is successfully processed.
    """
    user_model = get_user_model()
    enrollee = course_entitlement.user
    entitlement_uuid = str(course_entitlement.uuid)

    if not is_commerce_service_configured():
        log.error(
            'Ecommerce service is not configured, cannot refund for user [%s], course entitlement [%s].',
            enrollee.id,
            entitlement_uuid
        )
        return False

    service_user = user_model.objects.get(username=settings.ECOMMERCE_SERVICE_WORKER_USERNAME)
    api_client = ecommerce_api_client(service_user)

    log.info(
        'Attempting to create a refund for user [%s], course entitlement [%s]...',
        enrollee.id,
        entitlement_uuid
    )

    try:
        refund_ids = api_client.refunds.post(
            {
                'order_number': course_entitlement.order_number,
                'username': enrollee.username,
                'entitlement_uuid': entitlement_uuid,
            }
        )
    except Exception as exc:  # pylint: disable=broad-except
        # Catch any possible exceptions from the Ecommerce service to ensure we fail gracefully
        log.exception(
            "Unexpected exception while attempting to initiate refund for user [%s], "
            "course entitlement [%s] message: [%s]",
            enrollee.id,
            course_entitlement.uuid,
            str(exc)
        )
        return False

    if refund_ids:
        log.info(
            'Refund successfully opened for user [%s], course entitlement [%s]: %r',
            enrollee.id,
            entitlement_uuid,
            refund_ids,
        )

        return _process_refund(
            refund_ids=refund_ids,
            api_client=api_client,
            mode=course_entitlement.mode,
            user=enrollee,
            always_notify=True,
        )
    else:
        log.warn('No refund opened for user [%s], course entitlement [%s]', enrollee.id, entitlement_uuid)
        return False


def refund_seat(course_enrollment):
    """
    Attempt to initiate a refund for any orders associated with the seat being unenrolled,
    using the commerce service.

    Arguments:
        course_enrollment (CourseEnrollment): a student enrollment

    Returns:
        A list of the external service's IDs for any refunds that were initiated
            (may be empty).

    Raises:
        exceptions.SlumberBaseException: for any unhandled HTTP error during communication with the E-Commerce Service.
        exceptions.Timeout: if the attempt to reach the commerce service timed out.
    """
    User = get_user_model()  # pylint:disable=invalid-name
    course_key_str = unicode(course_enrollment.course_id)
    enrollee = course_enrollment.user

    service_user = User.objects.get(username=settings.ECOMMERCE_SERVICE_WORKER_USERNAME)
    api_client = ecommerce_api_client(service_user)

    log.info('Attempting to create a refund for user [%s], course [%s]...', enrollee.id, course_key_str)

    refund_ids = api_client.refunds.post({'course_id': course_key_str, 'username': enrollee.username})

    if refund_ids:
        log.info('Refund successfully opened for user [%s], course [%s]: %r', enrollee.id, course_key_str, refund_ids)

        _process_refund(
            refund_ids=refund_ids,
            api_client=api_client,
            mode=course_enrollment.mode,
            user=enrollee,
        )
    else:
        log.info('No refund opened for user [%s], course [%s]', enrollee.id, course_key_str)

    return refund_ids


def _process_refund(refund_ids, api_client, mode, user, always_notify=False):
    """
    Helper method to process a refund for a given course_product. This method assumes that the User has already
    been unenrolled.

    Arguments:
        refund_ids: List of refund ids to be processed
        api_client: The API Client used in the processing of refunds
        mode: The mode that the refund should be processed for
        user: The user that the refund is being processed for
        always_notify (bool): This will enable always notifying support with Zendesk tickets when
            an approval is required

    Returns:
        bool: True if the refund process was successful, False if there are any Errors that are not handled
    """
    config = CommerceConfiguration.current()

    if config.enable_automatic_refund_approval:
        refunds_requiring_approval = []

        for refund_id in refund_ids:
            try:
                # NOTE: The following assumes that the user has already been unenrolled.
                # We are then able to approve payment. Additionally, this ensures we don't tie up an
                # additional web worker when the E-Commerce Service tries to unenroll the learner.
                api_client.refunds(refund_id).process.put({'action': 'approve_payment_only'})
                log.info('Refund [%d] successfully approved.', refund_id)
            except:  # pylint: disable=bare-except
                # Push the refund to Support to process
                log.exception('Failed to automatically approve refund [%d]!', refund_id)
                refunds_requiring_approval.append(refund_id)
    else:
        refunds_requiring_approval = refund_ids

    if refunds_requiring_approval:
        # XCOM-371: this is a temporary measure to suppress refund-related email
        # notifications to students and support for free enrollments.  This
        # condition should be removed when the CourseEnrollment.refundable() logic
        # is updated to be more correct, or when we implement better handling (and
        # notifications) in Otto for handling reversal of $0 transactions.
        if mode != 'verified' and not always_notify:
            # 'verified' is the only enrollment mode that should presently
            # result in opening a refund request.
            log.info(
                'Skipping refund support notification for non-verified mode for user [%s], mode: [%s]',
                user.id,
                mode,
            )
        else:
            try:
                return _send_refund_notification(user, refunds_requiring_approval)
            except:  # pylint: disable=bare-except
                # Unable to send notification to Support, do not break as this method is used by Signals
                log.warning('Could not send support notification for refund.', exc_info=True)
                return False
    return True


def _send_refund_notification(user, refund_ids):
    """
    Notify the support team of the refund request.

    Returns:
        bool: True if we are able to send the notification.  In this case that means we were able to create
              a ZenDesk ticket
    """

    tags = ['auto_refund']

    if theming_helpers.is_request_in_themed_site():
        # this is not presently supported with the external service.
        raise NotImplementedError("Unable to send refund processing emails to support teams.")

    # Build the information for the ZenDesk ticket
    student = user
    subject = _("[Refund] User-Requested Refund")
    body = _generate_refund_notification_body(student, refund_ids)
    requester_name = student.profile.name or student.username

    return create_zendesk_ticket(requester_name, student.email, subject, body, tags)


def _generate_refund_notification_body(student, refund_ids):  # pylint: disable=invalid-name
    """ Returns a refund notification message body. """
    msg = _(
        'A refund request has been initiated for {username} ({email}). '
        'To process this request, please visit the link(s) below.'
    ).format(username=student.username, email=student.email)

    ecommerce_url_root = configuration_helpers.get_value(
        'ECOMMERCE_PUBLIC_URL_ROOT', settings.ECOMMERCE_PUBLIC_URL_ROOT,
    )
    refund_urls = [urljoin(ecommerce_url_root, '/dashboard/refunds/{}/'.format(refund_id))
                   for refund_id in refund_ids]

    # emails contained in this message could contain unicode characters so encode as such
    return u'{msg}\n\n{urls}'.format(msg=msg, urls='\n'.join(refund_urls))


def create_zendesk_ticket(requester_name, requester_email, subject, body, tags=None):
    """
    Create a Zendesk ticket via API.

    Returns:
        bool: False if we are unable to create the ticket for any reason
    """
    if not (settings.ZENDESK_URL and settings.ZENDESK_USER and settings.ZENDESK_API_KEY):
        log.error('Zendesk is not configured. Cannot create a ticket.')
        return False

    # Copy the tags to avoid modifying the original list.
    tags = set(tags or [])
    tags.add('LMS')
    tags = list(tags)

    data = {
        'ticket': {
            'requester': {
                'name': requester_name,
                'email': unicode(requester_email)
            },
            'subject': subject,
            'comment': {'body': body},
            'tags': tags
        }
    }

    # Encode the data to create a JSON payload
    payload = json.dumps(data)

    # Set the request parameters
    url = urljoin(settings.ZENDESK_URL, '/api/v2/tickets.json')
    user = '{}/token'.format(settings.ZENDESK_USER)
    pwd = settings.ZENDESK_API_KEY
    headers = {'content-type': 'application/json'}

    try:
        response = requests.post(url, data=payload, auth=(user, pwd), headers=headers)

        # Check for HTTP codes other than 201 (Created)
        if response.status_code != 201:
            log.error('Failed to create ticket. Status: [%d], Body: [%s]', response.status_code, response.content)
            return False
        else:
            log.debug('Successfully created ticket.')
    except Exception:  # pylint: disable=broad-except
        log.exception('Failed to create ticket.')
        return False
    return True
