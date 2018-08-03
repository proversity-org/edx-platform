import logging
import re

from django.conf import settings

from student.models import anonymous_id_for_user, get_user

LOG = logging.getLogger(__name__)


def get_rocket_chat_settings():
    """Return dict with rocket chat settings"""
    try:
        return settings.ROCKET_CHAT_SETTINGS
    except AttributeError, settings_error:
        LOG.warning('Get settings warning: %s', settings_error)
        pass
    try:
        xblock_settings = settings.XBLOCK_SETTINGS
        return xblock_settings.get('RocketChatXBlock', None)
    except AttributeError, xblock_settings_error:
        LOG.warning('Get settings warning: %s', xblock_settings_error)
        pass

    return None


def create_user(api_rocket_chat, user, course_key):
    """Create a user in rocketChat"""
    user, u_prof = get_user(user.email)
    anonymous_id = anonymous_id_for_user(user, course_key)
    api_rocket_chat.users_create(
        email=user.email,
        name=u_prof.name,
        password=anonymous_id,
        username=user.username
    )


def create_course_group(api_rocket_chat, course_id, user_id, username):
    """
    Add an user to the course group
    """
    room_name = re.sub('[^A-Za-z0-9]+', '', course_id)
    response = api_rocket_chat.groups_info(room_name=room_name)
    try:
        response = response.json()

        if response['success']:
            api_rocket_chat.groups_invite(response['group']['_id'], user_id)
        else:
            kwargs = {'members': [username]}
            api_rocket_chat.groups_create(name=room_name, **kwargs)

    except AttributeError:
        LOG.error("Create Course Group error: response with status code = %s", response.status_code)
        pass
