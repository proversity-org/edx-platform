"""
Badging service for XBlocks
"""
from badges.models import BadgeClass, BadgeAssertion


class BadgingService(object):
    """
    A class that provides functions for managing badges which XBlocks can use.

    If course_enabled is True, course-level badges are permitted for this course.

    If it is False, any badges that are awarded should be non-course specific.
    """
    course_badges_enabled = False

    def __init__(self, course_id=None, modulestore=None):
        """
        Sets the 'course_badges_enabled' parameter.
        """
        if not (course_id and modulestore):
            return

        course = modulestore.get_course(course_id)
        if course:
            self.course_badges_enabled = course.issue_badges

    get_badge_class = BadgeClass.get_badge_class
    assertions_for_user = BadgeAssertion.assertions_for_user
    slug_assertion_for_user = BadgeAssertion.slug_assertion_for_user

