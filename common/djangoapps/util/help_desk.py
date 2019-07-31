"""
Module containing helps desk factory function and help desk interfaces.
"""
import json
import logging
from abc import abstractmethod
from importlib import import_module

import requests
import zendesk
from django.conf import settings
from django.core.cache import cache
from opaque_keys.edx.keys import CourseKey

from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from student.models import CourseEnrollment

log = logging.getLogger(__name__)


class HelpDeskService(object):
    """
    Class containing the common logical for the help desk functionallity.
    """

    @abstractmethod
    def get_help_desk_service(self):
        """
        Returns the configured help desk service depending on HELP_DESK_SERVICE_BACKEND value.
        """
        help_desk_service = getattr(settings, 'HELP_DESK_SERVICE_BACKEND', '')

        if not help_desk_service:
            raise ValueError('HELP_DESK_SERVICE_BACKEND')

        module_string = help_desk_service.split(':')
        help_desk_class_string = module_string[-1]
        help_desk_module = import_module(module_string[0])

        return getattr(help_desk_module, help_desk_class_string)


class FreshdeskError(Exception):
    """
    FreshdeskError base exception.
    """
    def __init__(self, msg, code, response):
        self.msg = msg
        self.error_code = code
        self.response = response

    def __str__(self):
        return repr('%s: %s %s' % (self.error_code, self.msg, self.response))


class _FreshdeskApi(object):
    """
    Freshdesk API implementation.
    """

    CACHE_PREFIX = 'FRESHDESK_API_CACHE'
    CACHE_TIMEOUT = 60 * 60

    def __init__(self):
        """
        Instantiate the Freshdesk API.

        `HELPDESK_URL` and `HELPDESK_API_KEY` must be set
        Set `HELPDESK` = 'Freshdesk'
        in `django.conf.settings`.
        """


    def create_ticket(self, subject, desc, name, email, priority=1, status=2, group_id=None):
        """
        Create the given `ticket` in Freshdesk.

        The ticket should have the format specified by the freshdesk api.
        https://freshdesk.com/api#create_ticket
        """
        headers = {'Content-Type': 'application/json'}
        payload = {
            'subject': subject,
            'description': desc,
            'name': name,
            'email': email,
            'priority': priority,
            'status': status,
            'group_id': group_id
        }

        response = requests.post(
            settings.HELPDESK_URL + '/api/v2/tickets',
            auth=(settings.HELPDESK_API_KEY, "unused_but_required"),
            headers=headers,
            data=json.dumps(payload),
            allow_redirects=False)

        if response.ok:
            message = response.json()
            return message.get('id', '')
        else:
            raise FreshdeskError(response.content, response.status_code, response)


    def update_ticket(self, ticket_id, note, tags):
        """
        Update the Freshdeck ticket with id `ticket_id` using the given `note`.

        The update should have the format specified by the freshdesk api.
        https://freshdesk.com/api#add_note_to_a_ticket
        """
        headers = {'Content-Type': 'application/json'}
        payload = {
            "body" : note,
            "private" : True
        }

        response = requests.post(
            settings.HELPDESK_URL + '/api/v2/tickets/' + str(ticket_id) + '/notes',
            auth=(settings.HELPDESK_API_KEY, "unused_but_required"),
            headers=headers,
            data=json.dumps(payload),
            allow_redirects=False)

        if response.ok:
            return response.json()
        else:
            raise FreshdeskError(response.content, response.status_code, response)


    def get_group(self, name):
        """
        Find the Freshdesk group named `name`. Groups are cached for
        CACHE_TIMEOUT seconds.

        If a matching group exists, it is returned as a dictionary
        with the format specifed by the freshdesk api.

        Otherwise, returns None.
        """
        cache_key = '{prefix}_group_{name}'.format(prefix=self.CACHE_PREFIX, name=name)
        cached = cache.get(cache_key)
        if cached:
            return cached

        headers = {'Content-Type': 'application/json'}
        response = requests.get(
            settings.HELPDESK_URL + '/api/v2/groups',
            auth=(settings.HELPDESK_API_KEY, 'unused_but_required'),
            headers=headers,
            allow_redirects=False)

        groups = json.loads(response.content)

        if response.ok:
            for group in groups:
                if group.get('group', {}).get('name', '') == name:
                    cache.set(cache_key, group, self.CACHE_TIMEOUT)
                    return group
        else:
            raise FreshdeskError(groups, response.status_code, response)

        return None

    @abstractmethod
    def record_feedback(self, *args, **kwargs):
        """
        Returns the _record_feedback_in_freshdesk implementation.
        """
        return _record_feedback_in_freshdesk(*args, **kwargs)


def _record_feedback_in_freshdesk(
        realname,
        email,
        subject,
        details,
        tags,
        additional_info,
        group_name=None,
        require_update=False
):
    """
    Create a new user-requested Freshdesk ticket.

    Once created, the ticket will be updated with a private comment containing
    additional information from the browser and server, such as HTTP headers
    and user state. Returns a boolean value indicating whether ticket creation
    was successful, regardless of whether the private comment update succeeded.

    If `group_name` is provided, attaches the ticket to the matching Freshdesk group.

    If `require_update` is provided, returns False when the update does not
    succeed. This allows using the private comment to add necessary information
    which the user will not see in followup emails from support.
    """
    freshdesk_api = _FreshdeskApi()

    additional_info_string = (
        u'Additional information:\n\n' +
        u'\n'.join(u'%s: %s' % (key, value) for (key, value) in additional_info.items() if value is not None)
    )

    # Tag all issues with LMS to distinguish channel in Freshdesk; requested by student support team
    freshdesk_tags = list(tags.values()) + ['LMS']

    # Per edX support, we would like to be able to route white label feedback items
    # via tagging
    white_label_org = configuration_helpers.get_value('course_org_filter')
    if white_label_org:
        freshdesk_tags = freshdesk_tags + ['whitelabel_{org}'.format(org=white_label_org)]

    group_id = None
    if group_name:
        try:
            group = freshdesk_api.get_group(group_name)
            group_id = group.get('id', '')
        except FreshdeskError:
            log.warning('Cannot find Freshdesk group named: ' + group_name)

    try:
        ticket_id = freshdesk_api.create_ticket(subject, details, realname, email, 1, 2, group_id)
    except FreshdeskError:
        log.exception('Error creating Freshdesk ticket')
        return False

    # Additional information is provided as a private update so the information
    # is not visible to the user. https://freshdesk.com/api#add_note_to_a_ticket
    try:
        freshdesk_api.update_ticket(ticket_id, additional_info_string, freshdesk_tags)
    except FreshdeskError:
        log.exception('Error updating Freshdesk ticket with ID %s.', ticket_id)
        # The update is not strictly necessary, so do not indicate failure
        # to the user unless it has been requested with `require_update`.
        if require_update:
            return False
    return True


class _ZendeskApi(object):
    """
    Zendesk API implementation.
    """

    CACHE_PREFIX = 'ZENDESK_API_CACHE'
    CACHE_TIMEOUT = 60 * 60

    def __init__(self):
        """
        Instantiate the Zendesk API.

        All of `HELPDESK_URL`, `HELPDESK_USER`, and `HELPDESK_API_KEY` must be set
        in `django.conf.settings`.
        """
        self._zendesk_instance = zendesk.Zendesk(
            settings.HELPDESK_URL,
            settings.HELPDESK_USER,
            settings.HELPDESK_API_KEY,
            use_api_token=True,
            api_version=2,
            # As of 2012-05-08, Zendesk is using a CA that is not
            # installed on our servers
            client_args={"disable_ssl_certificate_validation": True}
        )

    def create_ticket(self, ticket):
        """
        Create the given `ticket` in Zendesk.

        The ticket should have the format specified by the zendesk package.
        """
        ticket_url = self._zendesk_instance.create_ticket(data=ticket)
        return zendesk.get_id_from_url(ticket_url)

    def update_ticket(self, ticket_id, update):
        """
        Update the Zendesk ticket with id `ticket_id` using the given `update`.

        The update should have the format specified by the zendesk package.
        """
        self._zendesk_instance.update_ticket(ticket_id=ticket_id, data=update)

    def get_group(self, name):
        """
        Find the Zendesk group named `name`. Groups are cached for
        CACHE_TIMEOUT seconds.

        If a matching group exists, it is returned as a dictionary
        with the format specifed by the zendesk package.

        Otherwise, returns None.
        """
        cache_key = '{prefix}_group_{name}'.format(prefix=self.CACHE_PREFIX, name=name)
        cached = cache.get(cache_key)
        if cached:
            return cached
        groups = self._zendesk_instance.list_groups()['groups']
        for group in groups:
            if group.get('name', '') == name:
                cache.set(cache_key, group, self.CACHE_TIMEOUT)
                return group
        return None

    @abstractmethod
    def record_feedback(self, *args, **kwargs):
        """
        Returns the _record_feedback_in_zendesk implementation.
        """
        return _record_feedback_in_zendesk(*args, **kwargs)


def _get_zendesk_custom_field_context(request, **kwargs):
    """
    Construct a dictionary of data that can be stored in Zendesk custom fields.
    """
    context = {}

    course_id = request.POST.get("course_id")
    if not course_id:
        return context

    context["course_id"] = course_id
    if not request.user.is_authenticated:
        return context

    enrollment = CourseEnrollment.get_enrollment(request.user, CourseKey.from_string(course_id))
    if enrollment and enrollment.is_active:
        context["enrollment_mode"] = enrollment.mode

    enterprise_learner_data = kwargs.get('learner_data', None)

    if enterprise_learner_data:
        enterprise_customer_name = enterprise_learner_data[0].get(
            'enterprise_customer',
            {}
        ).get('name', '')
        context["enterprise_customer_name"] = enterprise_customer_name

    return context


def _format_zendesk_custom_fields(context):
    """
    Format the data in `context` for compatibility with the Zendesk API.
    Ignore any keys that have not been configured in `ZENDESK_CUSTOM_FIELDS`.
    """
    custom_fields = []
    for key, val, in settings.ZENDESK_CUSTOM_FIELDS.items():
        if key in context:
            custom_fields.append({"id": val, "value": context[key]})

    return custom_fields


def _record_feedback_in_zendesk(
        realname,
        email,
        subject,
        details,
        tags,
        additional_info,
        group_name=None,
        require_update=False,
        support_email=None,
        custom_fields=None
):
    """
    Create a new user-requested Zendesk ticket.

    Once created, the ticket will be updated with a private comment containing
    additional information from the browser and server, such as HTTP headers
    and user state. Returns a boolean value indicating whether ticket creation
    was successful, regardless of whether the private comment update succeeded.

    If `group_name` is provided, attaches the ticket to the matching Zendesk group.

    If `require_update` is provided, returns False when the update does not
    succeed. This allows using the private comment to add necessary information
    which the user will not see in followup emails from support.

    If `custom_fields` is provided, submits data to those fields in Zendesk.
    """
    zendesk_api = _ZendeskApi()

    additional_info_string = (
        u"Additional information:\n\n" +
        u"\n".join(u"%s: %s" % (key, value) for (key, value) in additional_info.items() if value is not None)
    )

    # Tag all issues with LMS to distinguish channel in Zendesk; requested by student support team
    zendesk_tags = list(tags.values()) + ["LMS"]

    # Per edX support, we would like to be able to route feedback items by site via tagging
    current_site_name = configuration_helpers.get_value("SITE_NAME")
    if current_site_name:
        current_site_name = current_site_name.replace(".", "_")
        zendesk_tags.append("site_name_{site}".format(site=current_site_name))

    new_ticket = {
        "ticket": {
            "requester": {"name": realname, "email": email},
            "subject": subject,
            "comment": {"body": details},
            "tags": zendesk_tags
        }
    }

    if custom_fields:
        new_ticket["ticket"]["custom_fields"] = custom_fields

    group = None
    if group_name:
        group = zendesk_api.get_group(group_name)
        if group:
            new_ticket['ticket']['group_id'] = group.get('id', '')
    if support_email:
        # If we do not include the `recipient` key here, Zendesk will default to using its default reply
        # email address when support agents respond to tickets. By setting the `recipient` key here,
        # we can ensure that WL site users are responded to via the correct Zendesk support email address.
        new_ticket['ticket']['recipient'] = support_email
    try:
        ticket_id = zendesk_api.create_ticket(new_ticket)
        if group_name and not group:
            # Support uses Zendesk groups to track tickets. In case we
            # haven't been able to correctly group this ticket, log its ID
            # so it can be found later.
            log.warning('Unable to find group named %s for Zendesk ticket with ID %s.', group_name, ticket_id)
    except zendesk.ZendeskError:
        log.exception("Error creating Zendesk ticket")
        return False

    # Additional information is provided as a private update so the information
    # is not visible to the user.
    ticket_update = {"ticket": {"comment": {"public": False, "body": additional_info_string}}}
    try:
        zendesk_api.update_ticket(ticket_id, ticket_update)
    except zendesk.ZendeskError:
        log.exception("Error updating Zendesk ticket with ID %s.", ticket_id)
        # The update is not strictly necessary, so do not indicate
        # failure to the user unless it has been requested with
        # `require_update`.
        if require_update:
            return False
    return True
