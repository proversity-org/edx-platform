from celery import task  # pylint: disable=no-name-in-module
from opaque_keys.edx.keys import CourseKey

from student.models import CourseEnrollmentManager
from microsite_configuration import microsite
from lms.djangoapps.completion.utils import GenerateCompletionReport


@task(default_retry_delay=5, max_retries=5)
def generate_report(course_id, store_report, site_name):

    microsite.set_by_domain(site_name)

    course_key = CourseKey.from_string(course_id)
    users = CourseEnrollmentManager().users_enrolled_in(course_key)
    completion_report = GenerateCompletionReport(users, course_key)
    rows = completion_report.generate_rows()
    if store_report:
        return rows, completion_report.store_report(rows)
    return rows, None
