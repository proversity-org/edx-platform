"""HTTP end-points for the User API. """

from django.contrib.auth.models import User
from django.core.exceptions import NON_FIELD_ERRORS, PermissionDenied, ValidationError
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt, csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from django_filters.rest_framework import DjangoFilterBackend
from opaque_keys import InvalidKeyError
from opaque_keys.edx import locator
from opaque_keys.edx.keys import CourseKey
from rest_framework import authentication, generics, status, viewsets
from rest_framework.exceptions import ParseError
from rest_framework.views import APIView
from six import text_type

import accounts
from django_comment_common.models import Role
from openedx.core.djangoapps.user_api.accounts.api import check_account_exists
from openedx.core.djangoapps.user_api.api import (
    RegistrationFormFactory,
    get_login_session_form,
    get_password_reset_form
)
from openedx.core.djangoapps.user_api.helpers import require_post_params, shim_student_view
from openedx.core.djangoapps.user_api.models import UserPreference
from openedx.core.djangoapps.user_api.preferences.api import get_country_time_zones, update_email_opt_in
from openedx.core.djangoapps.user_api.serializers import CountryTimeZoneSerializer, UserPreferenceSerializer, UserSerializer
from openedx.core.lib.api.authentication import SessionAuthenticationAllowInactiveUser
from openedx.core.lib.api.permissions import ApiKeyHeaderPermission
from rest_framework_oauth.authentication import OAuth2Authentication
from student.cookies import set_logged_in_cookies
from student.views import AccountValidationError, create_account_with_params
from util.json_request import JsonResponse
from organizations.models import OrganizationCourse
from student.models import CourseEnrollment, Registration
import json
from util.organizations_helpers import get_organizations, get_organization_by_short_name
import logging

Log = logging.getLogger("openedx.core.djangoapps.user_api.view.py")


class LoginSessionView(APIView):
    """HTTP end-points for logging in users. """

    # This end-point is available to anonymous users,
    # so do not require authentication.
    authentication_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return HttpResponse(get_login_session_form(request).to_json(), content_type="application/json")

        """Return a description of the login form.

        This decouples clients from the API definition:
        if the API decides to modify the form, clients won't need
        to be updated.

        See `user_api.helpers.FormDescription` for examples
        of the JSON-encoded form description.

        Returns:
            HttpResponse

        """
        form_desc = FormDescription("post", reverse("user_api_login_session"))

        # Translators: This label appears above a field on the login form
        # meant to hold the user's email address.
        email_label = "%s %s %s" % (_(u"Username"), _(u"or"), _(u"email"))

        # Translators: This example email address is used as a placeholder in
        # a field on the login form meant to hold the user's email address.
        email_placeholder = "%s %s %s" % (_(u"username"), _(u"or"), _(u"username@domain.com"))

        # Translators: These instructions appear on the login form, immediately
        # below a field meant to hold the user's email address.
        email_instructions = _("The email address you used to register with {platform_name}").format(
            platform_name=configuration_helpers.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        )

        form_desc.add_field(
            "email",
            field_type="email",
            label=email_label,
            placeholder=email_placeholder,
            instructions=email_instructions,
            restrictions={
                "min_length": EMAIL_MIN_LENGTH,
                "max_length": EMAIL_MAX_LENGTH,
            }
        )

        # Translators: This label appears above a field on the login form
        # meant to hold the user's password.
        password_label = _(u"Password")

        form_desc.add_field(
            "password",
            label=password_label,
            field_type="password",
            restrictions={
                "min_length": PASSWORD_MIN_LENGTH,
                "max_length": PASSWORD_MAX_LENGTH,
            }
        )

        form_desc.add_field(
            "remember",
            field_type="checkbox",
            label=_("Remember me"),
            default=False,
            required=False,
        )

        return HttpResponse(form_desc.to_json(), content_type="application/json")


    @method_decorator(require_post_params(["email", "password"]))
    @method_decorator(csrf_protect)
    def post(self, request):
        """Log in a user.

        You must send all required form fields with the request.

        You can optionally send an `analytics` param with a JSON-encoded
        object with additional info to include in the login analytics event.
        Currently, the only supported field is "enroll_course_id" to indicate
        that the user logged in while enrolling in a particular course.

        Arguments:
            request (HttpRequest)

        Returns:
            HttpResponse: 200 on success
            HttpResponse: 400 if the request is not valid.
            HttpResponse: 403 if authentication failed.
                403 with content "third-party-auth" if the user
                has successfully authenticated with a third party provider
                but does not have a linked account.
            HttpResponse: 302 if redirecting to another page.

        Example Usage:

            POST /user_api/v1/login_session
            with POST params `email`, `password`, and `remember`.

            200 OK

        """
        # For the initial implementation, shim the existing login view
        # from the student Django app.
        from student.views import login_user
        return shim_student_view(login_user, check_logged_in=True)(request)

    @method_decorator(sensitive_post_parameters("password"))
    def dispatch(self, request, *args, **kwargs):
        return super(LoginSessionView, self).dispatch(request, *args, **kwargs)


class RegistrationView(APIView):
    """HTTP end-points for creating a new user. """

    # This end-point is available to anonymous users,
    # so do not require authentication.
    authentication_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return HttpResponse(RegistrationFormFactory().get_registration_form(request).to_json(),
                            content_type="application/json")

    @method_decorator(csrf_exempt)
    def post(self, request):
        """Create the user's account.

        You must send all required form fields with the request.

        You can optionally send a "course_id" param to indicate in analytics
        events that the user registered while enrolling in a particular course.

        Arguments:
            request (HTTPRequest)

        Returns:
            HttpResponse: 200 on success
            HttpResponse: 400 if the request is not valid.
            HttpResponse: 409 if an account with the given username or email
                address already exists
            HttpResponse: 403 operation not allowed
        """
        data = request.POST.copy()

        email = data.get('email')
        username = data.get('username')

        # Handle duplicate email/username
        conflicts = check_account_exists(email=email, username=username)
        if conflicts:
            conflict_messages = {
                "email": accounts.EMAIL_CONFLICT_MSG.format(email_address=email),
                "username": accounts.USERNAME_CONFLICT_MSG.format(username=username),
            }
            errors = {
                field: [{"user_message": conflict_messages[field]}]
                for field in conflicts
            }
            return JsonResponse(errors, status=409)

        # Backwards compatibility: the student view expects both
        # terms of service and honor code values.  Since we're combining
        # these into a single checkbox, the only value we may get
        # from the new view is "honor_code".
        # Longer term, we will need to make this more flexible to support
        # open source installations that may have separate checkboxes
        # for TOS, privacy policy, etc.
        if data.get("honor_code") and "terms_of_service" not in data:
            data["terms_of_service"] = data["honor_code"]

        # Enable use of BYPASS_ACTIVATION_FOR_USER_API
        request.session['is_user_api_registration'] = True

        try:
            user = create_account_with_params(request, data)
        except AccountValidationError as err:
            errors = {
                err.field: [{"user_message": text_type(err)}]
            }
            return JsonResponse(errors, status=409)
        except ValidationError as err:
            # Should only get non-field errors from this function
            assert NON_FIELD_ERRORS not in err.message_dict
            # Only return first error for each field
            errors = {
                field: [{"user_message": error} for error in error_list]
                for field, error_list in err.message_dict.items()
            }
            return JsonResponse(errors, status=400)
        except PermissionDenied:
            return HttpResponseForbidden(_("Account creation not allowed."))

        response = JsonResponse({"success": True})
        set_logged_in_cookies(request, response, user)
        return response

    @method_decorator(sensitive_post_parameters("password"))
    def dispatch(self, request, *args, **kwargs):
        return super(RegistrationView, self).dispatch(request, *args, **kwargs)


class PasswordResetView(APIView):
    """HTTP end-point for GETting a description of the password reset form. """

    # This end-point is available to anonymous users,
    # so do not require authentication.
    authentication_classes = []

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return HttpResponse(get_password_reset_form().to_json(), content_type="application/json")


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    DRF class for interacting with the User ORM object
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (ApiKeyHeaderPermission,)
    queryset = User.objects.all().prefetch_related("preferences").select_related("profile")
    serializer_class = UserSerializer
    paginate_by = 10
    paginate_by_param = "page_size"


class ForumRoleUsersListView(generics.ListAPIView):
    """
    Forum roles are represented by a list of user dicts
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (ApiKeyHeaderPermission,)
    serializer_class = UserSerializer
    paginate_by = 10
    paginate_by_param = "page_size"

    def get_queryset(self):
        """
        Return a list of users with the specified role/course pair
        """
        name = self.kwargs['name']
        course_id_string = self.request.query_params.get('course_id')
        if not course_id_string:
            raise ParseError('course_id must be specified')
        course_id = CourseKey.from_string(course_id_string)
        role = Role.objects.get_or_create(course_id=course_id, name=name)[0]
        users = role.users.prefetch_related("preferences").select_related("profile").all()
        return users


class UserPreferenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    DRF class for interacting with the UserPreference ORM
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (ApiKeyHeaderPermission,)
    queryset = UserPreference.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ("key", "user")
    serializer_class = UserPreferenceSerializer
    paginate_by = 10
    paginate_by_param = "page_size"


class PreferenceUsersListView(generics.ListAPIView):
    """
    DRF class for listing a user's preferences
    """
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (ApiKeyHeaderPermission,)
    serializer_class = UserSerializer
    paginate_by = 10
    paginate_by_param = "page_size"

    def get_queryset(self):
        return User.objects.filter(
            preferences__key=self.kwargs["pref_key"]
        ).prefetch_related("preferences").select_related("profile")


class UpdateEmailOptInPreference(APIView):
    """View for updating the email opt in preference. """
    authentication_classes = (SessionAuthenticationAllowInactiveUser,)

    @method_decorator(require_post_params(["course_id", "email_opt_in"]))
    @method_decorator(ensure_csrf_cookie)
    def post(self, request):
        """ Post function for updating the email opt in preference.

        Allows the modification or creation of the email opt in preference at an
        organizational level.

        Args:
            request (Request): The request should contain the following POST parameters:
                * course_id: The slash separated course ID. Used to determine the organization
                    for this preference setting.
                * email_opt_in: "True" or "False" to determine if the user is opting in for emails from
                    this organization. If the string does not match "True" (case insensitive) it will
                    assume False.

        """
        course_id = request.data['course_id']
        try:
            org = locator.CourseLocator.from_string(course_id).org
        except InvalidKeyError:
            return HttpResponse(
                status=400,
                content="No course '{course_id}' found".format(course_id=course_id),
                content_type="text/plain"
            )
        # Only check for true. All other values are False.
        email_opt_in = request.data['email_opt_in'].lower() == 'true'
        update_email_opt_in(request.user, org, email_opt_in)
        return HttpResponse(status=status.HTTP_200_OK)


class CountryTimeZoneListView(generics.ListAPIView):
    """
    **Use Cases**

        Retrieves a list of all time zones, by default, or common time zones for country, if given

        The country is passed in as its ISO 3166-1 Alpha-2 country code as an
        optional 'country_code' argument. The country code is also case-insensitive.

    **Example Requests**

        GET /user_api/v1/preferences/time_zones/

        GET /user_api/v1/preferences/time_zones/?country_code=FR

    **Example GET Response**

        If the request is successful, an HTTP 200 "OK" response is returned along with a
        list of time zone dictionaries for all time zones or just for time zones commonly
        used in a country, if given.

        Each time zone dictionary contains the following values.

            * time_zone: The name of the time zone.
            * description: The display version of the time zone
    """
    serializer_class = CountryTimeZoneSerializer
    paginator = None

    def get_queryset(self):
        country_code = self.request.GET.get('country_code', None)
        return get_country_time_zones(country_code)


class DeleteUserView(APIView):

    authentication_classes =\
        (OAuth2Authentication,)

    def post(self, request):
        try:
            data = request.data.get("users", None)
            if data is None:
                return JsonResponse({"Error": "No users to delete list given empty"})
            else:
                user_list = data.split(",")
            results = {}
            for user_name in user_list:
                results[user_name] = self._delete_user(user_name)

            return JsonResponse(results)
        except Exception as e:
            return JsonResponse({"Error": "Failed to delete users: {}".format(e.message)})


    def _delete_user(self, uname):
        """Deletes a user from django auth"""

        if not uname:
            return _('Must provide username')
        if '@' in uname:
            try:
                user = User.objects.get(email=uname)
            except User.DoesNotExist, err:
                msg = _('Cannot find user with email address {email_addr}').format(email_addr=uname)
                return msg
        else:
            try:
                user = User.objects.get(username=uname)
            except User.DoesNotExist, err:
                msg = _('Cannot find user with username {username} - {error}').format(
                    username=uname,
                    error=str(err)
                )
                return msg
        user.delete()
        return _('Deleted user {username}').format(username=uname)


class UserAnaliticsView(APIView):
    """
    **Use Cases**

        Retrieves a json dictionary of all enrolled users listed per course and per organization

    **Example Requests**

        GET /user_api/v1/userorg/?org=AWE

        GET /user_api/v1/userorg/?org=ALL

    **Example GET Response**

        If the request is successful, an HTTP 200 "OK" response is returned along with a
        disctionary containing all enrolled users catogarized per course and per organization

        PARAM: org - the organizations for which to get the enrolled users
                   - ALL = all organizations will be considered.

    """

    authentication_classes =\
        (OAuth2Authentication,)

    def get(self, request):
        """Handles the incomming request"""

        if not request.user.is_staff:
            return HttpResponse(status=status.HTTP_403_FORBIDDEN)

        org_filter = request.GET.get('org', None)
        data = ()
        enrollment_list = CourseEnrollment.objects.all()

        if org_filter is None or org_filter == 'All':
            data = data + (self._get_total_courses_for_all_orgs(),)
            data = data + (self._get_total_users_for_all_orgs(enrollment_list),)
        else:
            data = data + (self._get_total_courses_for_org(org_filter),)
            data = data + (self._get_total_users_for_org(org_filter, enrollment_list),)


        data = data + ({"Total unique enrollments": self._get_unique_enrollments_total(enrollment_list)},)
        data = data + (self._get_total_registered_users(),)
        data = data + (self._get_total_organizations(),)
        data = data + (self._get_enrollment_totals(enrollment_list),)

        return JsonResponse(data)


    def _get_unique_enrollments_total(self, enrollment_list):
        """
        Takes the given enrollment_list and makes it unique
        """
        unique_list = []
        for enrollment in enrollment_list:
            try:
                if enrollment.user.email not in unique_list:
                    unique_list.append(enrollment.user.email)
            except User.DoesNotExist:
                pass
        return len(unique_list)


    def _get_total_registered_users(self):
        """
        retrieves the total of registered users from the platform
        """
        try:            
            return {"Total Active Registrations": Registration.objects.filter(user__is_active=True).count()}
        except Exception as err:
            Log.error("Total Active Registrations, An error accured while trying to get the total registrations, ERROR = {}".format(err))
            return {"Total Active Registrations, Error": "An error accured while trying to get the total registrations, ERROR = {}".format(err)}


    def _get_total_organizations(self):
        """
        retreives the total number of configured Organizations from the Organizations app
        """

        try:
            total_orgs = get_organizations()
            return {"Total Organizations": len(total_orgs)}
        except Exception as err:
            Log.error("Total Organizations, An error accured while trying to get the total organizations, ERROR = {}".format(err))
            return {"Total Organizations, Error": "An error accured while trying to get the total organizations, ERROR = {}".format(err)}


    def _get_enrollment_totals(self, enrollment_list):
        """
        retreives the total of enrolled users, listing active and non active enrollments
        """

        try:
            total_enrolled_users_active = enrollment_list.filter(is_active=True).count()
            total_enrolled_users_not_active = enrollment_list.filter(is_active=False).count()

            return {
                    "Total Enrollments": total_enrolled_users_active + total_enrolled_users_not_active,
                    "Total Enrollments - Active": total_enrolled_users_active,
                    "Total Enrollments - NOT Active": total_enrolled_users_not_active
                   }
        except Exception as err:
            Log.error("Total Enrollments, An error accured while trying to get the total enrolled users, ERROR = {}".format(err))
            return {"Total Enrollments, Error": "An error accured while trying to get the total enrolled users, ERROR = {}".format(err)}


    def _get_total_courses_for_all_orgs(self):
        """
        retrieves all organizations and then calculates total courses per org
        """

        data = {}
        all_orgs = get_organizations()
        for org in all_orgs:
            data.update(self._get_total_courses_for_org(org['short_name']))

        return data



    def _get_total_courses_for_org(self, org_short_name=None):
        """
        retrieves the total number of courses linked to the given organization
        """

        try:
            total_courses = OrganizationCourse.objects.filter(organization__short_name=org_short_name).filter(active=True).count()
            return {"Total courses for {}".format(org_short_name): total_courses}
        except Exception as err:
            Log.error("Total Courses, An error accured while trying to get the total courses, ERROR = {}".format(err.message))
            return {"Total Courses, Error": "An error accured while trying to get the total courses, ERROR = {}".format(err.message)}


    def _get_total_users_for_all_orgs(self, enrollment_list):
        """
        retrieves the total number of enrolled users per organization
        """
        data = {}
        all_orgs = get_organizations()
        for org in all_orgs:
            data.update(self._get_total_users_for_org(org['short_name'], enrollment_list))

        return data


    def _get_total_users_for_org(self, org_short_name, enrollment_list):
        """
        retrieves the total number of enrolled users for the given organization
        Caveat, the User object does not have a direct link to the ORG object in the database,
        so we have to get all CourseEnrollments for thee given organization,
        and loop over the courses grabing the count() of each CourseEnrollment
        """
        total_users = 0
        org_courses = OrganizationCourse.objects.filter(organization__short_name=org_short_name)
        for course in org_courses:
            try:
                total_users = total_users + enrollment_list.filter(course_id=CourseKey.from_string(course.course_id)).count()
            except Exception as err:
                Log.error("Unable to get count for CourseEnrollment on course {}".format(course.course_id))
                return {"Unable to get count for CourseEnrollment on course {}".format(course.course_id)}

        return {"Total Enrollments for {}".format(org_short_name): total_users}
