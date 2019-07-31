import json
import logging
import sys

from functools import wraps
from smtplib import SMTPException
import crum

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.validators import ValidationError, validate_email
from django.http import Http404, HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseServerError
from django.views.decorators.csrf import requires_csrf_token
from django.views.defaults import server_error
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

import calc
import track.views
from edxmako.shortcuts import render_to_response, render_to_string
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.features.enterprise_support import api as enterprise_api
from student.roles import GlobalStaff
from util.help_desk import HelpDeskService

log = logging.getLogger(__name__)

DATADOG_FEEDBACK_METRIC = "lms_feedback_submissions"
SUPPORT_BACKEND_ZENDESK = "support_ticket"
SUPPORT_BACKEND_EMAIL = "email"


def ensure_valid_course_key(view_func):
    """
    This decorator should only be used with views which have argument course_key_string (studio) or course_id (lms).
    If course_key_string (studio) or course_id (lms) is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        course_key = kwargs.get('course_key_string') or kwargs.get('course_id')
        if course_key is not None:
            try:
                CourseKey.from_string(course_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


def ensure_valid_usage_key(view_func):
    """
    This decorator should only be used with views which have argument usage_key_string.
    If usage_key_string is not valid raise 404.
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):  # pylint: disable=missing-docstring
        usage_key = kwargs.get('usage_key_string')
        if usage_key is not None:
            try:
                UsageKey.from_string(usage_key)
            except InvalidKeyError:
                raise Http404

        response = view_func(request, *args, **kwargs)
        return response

    return inner


def require_global_staff(func):
    """View decorator that requires that the user have global staff permissions. """
    @wraps(func)
    def wrapped(request, *args, **kwargs):  # pylint: disable=missing-docstring
        if GlobalStaff().has_user(request.user):
            return func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden(
                u"Must be {platform_name} staff to perform this action.".format(
                    platform_name=settings.PLATFORM_NAME
                )
            )
    return login_required(wrapped)


def fix_crum_request(func):
    """
    A decorator that ensures that the 'crum' package (a middleware that stores and fetches the current request in
    thread-local storage) can correctly fetch the current request. Under certain conditions, the current request cannot
    be fetched by crum (e.g.: when HTTP errors are raised in our views via 'raise Http404', et. al.). This decorator
    manually sets the current request for crum if it cannot be fetched.
    """
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if not crum.get_current_request():
            crum.set_current_request(request=request)
        return func(request, *args, **kwargs)
    return wrapper


@requires_csrf_token
def jsonable_server_error(request, template_name='500.html'):
    """
    500 error handler that serves JSON on an AJAX request, and proxies
    to the Django default `server_error` view otherwise.
    """
    if request.is_ajax():
        msg = {"error": "The edX servers encountered an error"}
        return HttpResponseServerError(json.dumps(msg))
    else:
        return server_error(request, template_name=template_name)


def handle_500(template_path, context=None, test_func=None):
    """
    Decorator for view specific 500 error handling.
    Custom handling will be skipped only if test_func is passed and it returns False

    Usage:

        @handle_500(
            template_path='certificates/server-error.html',
            context={'error-info': 'Internal Server Error'},
            test_func=lambda request: request.GET.get('preview', None)
        )
        def my_view(request):
            # Any unhandled exception in this view would be handled by the handle_500 decorator
            # ...

    """
    def decorator(func):
        """
        Decorator to render custom html template in case of uncaught exception in wrapped function
        """
        @wraps(func)
        def inner(request, *args, **kwargs):
            """
            Execute the function in try..except block and return custom server-error page in case of unhandled exception
            """
            try:
                return func(request, *args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                if settings.DEBUG:
                    # In debug mode let django process the 500 errors and display debug info for the developer
                    raise
                elif test_func is None or test_func(request):
                    # Display custom 500 page if either
                    #   1. test_func is None (meaning nothing to test)
                    #   2. or test_func(request) returns True
                    log.exception("Error in django view.")
                    return render_to_response(template_path, context)
                else:
                    # Do not show custom 500 error when test fails
                    raise
        return inner
    return decorator


def calculate(request):
    ''' Calculator in footer of every page. '''
    equation = request.GET['equation']
    try:
        result = calc.evaluator({}, {}, equation)
    except:
        event = {'error': map(str, sys.exc_info()),
                 'equation': equation}
        track.views.server_track(request, 'error:calc', event, page='calc')
        return HttpResponse(json.dumps({'result': 'Invalid syntax'}))
    return HttpResponse(json.dumps({'result': str(result)}))


def get_feedback_form_context(request):
    """
    Extract the submitted form fields to be used as a context for
    feedback submission.
    """
    context = {}

    context["subject"] = request.POST["subject"]
    context["details"] = request.POST["details"]
    context["tags"] = dict(
        [(tag, request.POST[tag]) for tag in ["issue_type", "course_id"] if request.POST.get(tag)]
    )

    context["additional_info"] = {}

    if request.user.is_authenticated:
        context["realname"] = request.user.profile.name
        context["email"] = request.user.email
        context["additional_info"]["username"] = request.user.username
    else:
        context["realname"] = request.POST["name"]
        context["email"] = request.POST["email"]

    for header, pretty in [("HTTP_REFERER", "Page"), ("HTTP_USER_AGENT", "Browser"), ("REMOTE_ADDR", "Client IP"),
                           ("SERVER_NAME", "Host")]:
        context["additional_info"][pretty] = request.META.get(header)

    context["support_email"] = configuration_helpers.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)

    return context


def submit_feedback(request):
    """
    Create a new user-requested ticket, currently implemented with Zendesk/Freshdesk.

    If feedback submission is not enabled, any request will raise `Http404`.
    If any configuration parameter is missing, any request will raise an `Exception`.
    The request must be a POST request specifying `subject` and `details`.
    If the user is not authenticated, the request must also specify `name` and
    `email`. If the user is authenticated, the `name` and `email` will be
    populated from the user's information. If any required parameter is
    missing, a 400 error will be returned indicating which field is missing and
    providing an error message. If ticket creation fails, 500 error
    will be returned with no body; if ticket creation succeeds, an empty
    successful response (200) will be returned.
    """
    if not settings.FEATURES.get('ENABLE_FEEDBACK_SUBMISSION', False):
        raise Http404()
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    def build_error_response(status_code, field, err_msg):
        return HttpResponse(json.dumps({"field": field, "error": err_msg}), status=status_code)

    required_fields = ["subject", "details"]

    if not request.user.is_authenticated:
        required_fields += ["name", "email"]

    required_field_errs = {
        "subject": "Please provide a subject.",
        "details": "Please provide details.",
        "name": "Please provide your name.",
        "email": "Please provide a valid e-mail.",
    }
    for field in required_fields:
        if field not in request.POST or not request.POST[field]:
            return build_error_response(400, field, required_field_errs[field])

    if not request.user.is_authenticated:
        try:
            validate_email(request.POST["email"])
        except ValidationError:
            return build_error_response(400, "email", required_field_errs["email"])

    success = False
    context = get_feedback_form_context(request)

    # Update the tag info with 'enterprise_learner' if the user belongs to an enterprise customer.
    enterprise_learner_data = enterprise_api.get_enterprise_learner_data(user=request.user)
    if enterprise_learner_data:
        context["tags"]["learner_type"] = "enterprise_learner"

    support_backend = configuration_helpers.get_value('CONTACT_FORM_SUBMISSION_BACKEND', SUPPORT_BACKEND_ZENDESK)

    if support_backend == SUPPORT_BACKEND_EMAIL:
        try:
            send_mail(
                subject=render_to_string('emails/contact_us_feedback_email_subject.txt', context),
                message=render_to_string('emails/contact_us_feedback_email_body.txt', context),
                from_email=context["support_email"],
                recipient_list=[context["support_email"]],
                fail_silently=False
            )
            success = True
        except SMTPException:
            log.exception('Error sending feedback to contact_us email address.')
            success = False

    else:
        if not settings.HELPDESK_URL or not settings.HELPDESK_USER or not settings.HELPDESK_API_KEY:
            raise Exception("Helpdesk enabled but not configured")

        help_desk_service = HelpDeskService().get_help_desk_service()

        success = help_desk_service().record_feedback(
            context["realname"],
            context["email"],
            context["subject"],
            context["details"],
            context["tags"],
            context["additional_info"],
        )

    return HttpResponse(status=(200 if success else 500))


def info(request):
    ''' Info page (link from main header) '''
    # pylint: disable=unused-argument
    return render_to_response("info.html", {})


# From http://djangosnippets.org/snippets/1042/
def parse_accept_header(accept):
    """Parse the Accept header *accept*, returning a list with pairs of
    (media_type, q_value), ordered by q values.
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0)
        media_params = []
        q = 1.0
        for part in parts:
            (key, value) = part.lstrip().split("=", 1)
            if key == "q":
                q = float(value)
            else:
                media_params.append((key, value))
        result.append((media_type, tuple(media_params), q))
    result.sort(lambda x, y: -cmp(x[2], y[2]))
    return result


def accepts(request, media_type):
    """Return whether this request has an Accept header that matches type"""
    accept = parse_accept_header(request.META.get("HTTP_ACCEPT", ""))
    return media_type in [t for (t, p, q) in accept]


def add_p3p_header(view_func):
    """
    This decorator should only be used with views which may be displayed through the iframe.
    It adds additional headers to response and therefore gives IE browsers an ability to save cookies inside the iframe
    Details:
    http://blogs.msdn.com/b/ieinternals/archive/2013/09/17/simple-introduction-to-p3p-cookie-blocking-frame.aspx
    http://stackoverflow.com/questions/8048306/what-is-the-most-broad-p3p-header-that-will-work-with-ie
    """
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        """
        Helper function
        """
        response = view_func(request, *args, **kwargs)
        response['P3P'] = settings.P3P_HEADER
        return response
    return inner
