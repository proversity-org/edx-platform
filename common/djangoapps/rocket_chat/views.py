import logging

from django.http import Http404
from django.contrib.auth.decorators import login_required

from edxmako.shortcuts import render_to_response
from opaque_keys.edx.keys import CourseKey

from courseware.access import has_access
from courseware.courses import get_course_with_access
from student.models import CourseEnrollment

from xmodule.modulestore.django import modulestore
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers

from rocketchat_API.rocketchat import RocketChat as ApiRocketChat
from rocketchat_API.APIExceptions.RocketExceptions import RocketAuthenticationException, RocketConnectionException

from .utils import create_course_group, create_user, get_rocket_chat_settings

LOG = logging.getLogger(__name__)


@login_required
def rocket_chat_discussion(request, course_id):

    if not configuration_helpers.get_value('ENABLE_ROCKET_CHAT_SERVICE'):
        raise Http404

    course_key = CourseKey.from_string(course_id)

    with modulestore().bulk_operations(course_key):

        user = request.user
        course = get_course_with_access(user, 'load', course_key)

        staff_access = has_access(user, 'staff', course)
        user_is_enrolled = CourseEnrollment.is_enrolled(user, course.id)

        course_homepage_invert_title = configuration_helpers.get_value(
            'COURSE_HOMEPAGE_INVERT_TITLE', False)

        course_title = course.display_name_with_default
        if course_homepage_invert_title:
            course_title = course.display_number_with_default

        context = {
            'request': request,
            'cache': None,
            'course': course,
            'course_title': course_title,
            'staff_access': staff_access,
            'user_is_enrolled': user_is_enrolled,
        }

        rocket_chat_settings = get_rocket_chat_settings()

        if rocket_chat_settings:

            admin_user = rocket_chat_settings.get('admin_user', None)
            admin_pass = rocket_chat_settings.get('admin_pass', None)
            url_service = rocket_chat_settings.get('public_url_service', None)

            if not admin_user or not admin_pass or not url_service:
                LOG.error(
                    'RocketChat settings error: admin_user = %s, admin_pass= %s, public_url_service= %s',
                    admin_user,
                    admin_pass,
                    url_service
                )
                context['rocket_chat_error_message'] = 'Rocket chat service is currently not available'
                return render_to_response('rocket_chat/rocket_chat.html', context)

            try:
                api_rocket_chat = ApiRocketChat(
                    admin_user,
                    admin_pass,
                    url_service
                )
            except RocketAuthenticationException:

                LOG.error('ApiRocketChat error: RocketAuthenticationException')
                context['rocket_chat_error_message'] = 'Rocket chat service is currently not available'

                return render_to_response('rocket_chat/rocket_chat.html', context)

            except RocketConnectionException:

                LOG.error('ApiRocketChat error: RocketConnectionException')
                context['rocket_chat_error_message'] = 'Rocket chat service is currently not available'

                return render_to_response('rocket_chat/rocket_chat.html', context)

            user_info = api_rocket_chat.users_info(username=user.username)

            try:
                user_info = user_info.json()
            except AttributeError:
                create_user(api_rocket_chat, user, course_key)

            if 'success' in user_info and not user_info['success']:
                create_user(api_rocket_chat, user, course_key)

            response = api_rocket_chat.users_create_token(
                username=user.username)

            try:
                response = response.json()
            except AttributeError:
                context['rocket_chat_error_message'] = 'status_code = {}'.format(
                    response.status_code)
                return render_to_response('rocket_chat/rocket_chat.html', context)

            if response['success']:
                context['rocket_chat_data'] = response['data']
                context['rocket_chat_url'] = rocket_chat_settings['public_url_service']
                context['rocket_chat_error_message'] = None

                create_course_group(api_rocket_chat, course_id, response['data']['userId'], user.username)

            elif 'error' in response:
                context['rocket_chat_error_message'] = response['error']

            return render_to_response('rocket_chat/rocket_chat.html', context)

        context['rocket_chat_error_message'] = 'Rocket chat service is currently not available'

        return render_to_response('rocket_chat/rocket_chat.html', context)
