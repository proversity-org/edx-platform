"""
App Configuration for Completion
"""

from __future__ import absolute_import, division, print_function, unicode_literals
from django.apps import AppConfig


class CompletionAppConfig(AppConfig):
    """
    App Configuration for Completion
    """
    name = 'lms.djangoapps.completion'
    verbose_name = 'Completion'

    def ready(self):
        from . import handlers  # pylint: disable=unused-variable
        # The line below allows tasks defined in this app to be included by celery workers
        from .tasks import *  # pylint: disable=unused-variable
