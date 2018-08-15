"""
API v1 URLs.
"""
from django.conf import settings
from django.conf.urls import url

from . import views

TASK_ID_PATTERN = r'(?P<task_id>[a-z\d_-]+)'

urlpatterns = [
    url(r'^completion-batch', views.CompletionBatchView.as_view(), name='completion-batch'),
    url(
        r'^completion-report/{course_id_pattern}$'.format(
            course_id_pattern=settings.COURSE_ID_PATTERN,
        ),
        views.CompletionReportView.as_view(),
        name='completion-report'
    ),
    url(
        r'^completion-report/{task_id_pattern}/status/$'.format(
            task_id_pattern=TASK_ID_PATTERN,
        ),
        views.CompletionReportView.as_view(),
        name='completion-task-report'
    ),

    url(
        r'^download-completion-report/{task_id_pattern}/$'.format(
            task_id_pattern=TASK_ID_PATTERN,
        ),
        views.DownloadReportView.as_view(),
        name='download-completion-report'
    ),
]
