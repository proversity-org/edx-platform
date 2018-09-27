from celery import task  # pylint: disable=no-name-in-module
from opaque_keys.edx.keys import CourseKey

from django.contrib.auth.models import User

from lms.djangoapps.completion.utils import GenerateCompletionReport


@task(default_retry_delay=5, max_retries=5)
def generate_report(course_id, store_report):

    course_key = CourseKey.from_string(course_id)

    # Getting all students enrolled on the course except staff users
    enrolled_students = User.objects.filter(
        courseenrollment__course_id=course_key,
        courseenrollment__is_active=1,
        is_staff=0,
    )
    completion_report = GenerateCompletionReport(enrolled_students, course_key)
    rows = completion_report.generate_rows()
    if store_report:
        return rows, completion_report.store_report(rows)
    return rows, None
