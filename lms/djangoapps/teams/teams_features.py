"""Methods for teams modifications"""
from courseware.courses import get_course_by_id
from student.models import CourseEnrollmentManager
from opaque_keys.edx.locator import BlockUsageLocator
from opaque_keys import InvalidKeyError

CONTENT_DEPTH = 2


class CourseTeamsFeatures(object):
    """A class that provides the necessary settings and info for teams"""
    def __init__(self, course_key):
        course = get_course_by_id(course_key, CONTENT_DEPTH)
        self.course_key = course_key
        self.teams_configuration = course.teams_configuration

    def get_replacement_locator(self):
        """
        This method returns the locator for a unit, to do that this gets the unit location_id
        from teams_configuration, to set that go to studion->advanced settings-> teams_configuration
        """
        try:
            block_id = self.teams_configuration["replacement_location_id"]
            block_type = "vertical"
            locator = BlockUsageLocator(self.course_key, block_type, block_id)
            return locator
        except (KeyError, InvalidKeyError):
            return None

    def get_users_enrolled(self):
        """Return a generator with the username of every user in the course"""
        users = CourseEnrollmentManager().users_enrolled_in(self.course_key)
        for user in users:
            yield user.username

    def is_teams_locked(self):
        """Returns if teams is locked, this setting can be configured on studio"""
        return self.teams_configuration.get("teams_locked")

    def is_discussion_disable(self):
        """Returns if discussion is disabled, this setting can be configured on studio"""
        return self.teams_configuration.get("disable_default_discussion")
