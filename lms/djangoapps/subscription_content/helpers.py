""" Subscription content helpers. """

import logging
from django.conf import settings
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from xmodule.modulestore.django import modulestore

from student.views import is_course_blocked, get_org_black_and_whitelist_for_site, get_course_enrollments

log = logging.getLogger(__name__)

def get_subscription_catalog_id(course_id):
	course_store = modulestore().get_course(course_id)
	return course_store.subscription_catalog_id

def get_subscription_catalog_ids(user, course_enrollments=None):
	if not course_enrollments:
		site_org_whitelist, site_org_blacklist = get_org_black_and_whitelist_for_site(user)
		course_enrollments = list(get_course_enrollments(user, site_org_whitelist, site_org_blacklist))
		course_enrollments.sort(key=lambda x: x.created, reverse=True)
	subscription_courses = frozenset(
		get_subscription_catalog_id(enrollment.course_id)
		for enrollment in course_enrollments
	)
	return filter(None, subscription_courses)
