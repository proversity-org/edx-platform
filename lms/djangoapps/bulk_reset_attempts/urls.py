"""
URLs for the Bulk Enrollment API
"""
from django.conf.urls import patterns, url

from bulk_reset_attempts.views import BulkResetStudentAttemptsView

urlpatterns = patterns(
    'bulk_reset_attempts.views',
    url(r'^bulk_reset_student_attempts$', BulkResetStudentAttemptsView.as_view(), name="bulk_reset_student_attempts"),
)
