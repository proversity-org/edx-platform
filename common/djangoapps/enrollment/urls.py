"""
URLs for the Enrollment API

"""
from django.conf import settings
from django.conf.urls import patterns, url

from .views import EnrollmentCourseDetailView, EnrollmentListView, EnrollmentView, UnenrollmentView


    url(r'^enrollment$', EnrollmentListView.as_view(), name='courseenrollments'),

    url(r'^course/{course_key}$'.format(course_key=settings.COURSE_ID_PATTERN),
        EnrollmentCourseDetailView.as_view(), name='courseenrollmentdetails'),
    url(r'^unenroll$', UnenrollmentView.as_view(), name='unenrollment'),
]

