"""Methods for teams modifications"""
from courseware.courses import get_course_by_id
from student.models import CourseEnrollmentManager
from opaque_keys.edx.locator import BlockUsageLocator
from opaque_keys import InvalidKeyError

CONTENT_DEPTH = 2

def get_replacement_location_id(course_key):
    """
    This method gets the locator for a unique component in a unit.
    """
    course = get_course_by_id(course_key, CONTENT_DEPTH)

    try:
        block_id = course.teams_configuration["replacement_location_id"]
        block_type = "vertical"
        locator = BlockUsageLocator(course_key, block_type, block_id)
        return locator
    except (KeyError, InvalidKeyError):
        return None

def get_users_enrolled(course_key):
    """Return a generator with the username of every user in the course"""
    users = CourseEnrollmentManager().users_enrolled_in(course_key)
    for user in users:
        yield user.username
