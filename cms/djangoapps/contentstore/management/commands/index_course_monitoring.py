""" Management command to update courses' search index """
import logging
from textwrap import dedent

from django.core.management import BaseCommand

from contentstore.tasks import course_index_monitoring
from celery.result import AsyncResult
from django.conf import settings

class Command(BaseCommand):
    """
    Command to index courses monitoring

    Examples:

        ./manage.py index_course_monitoring
    """
    help = dedent(__doc__)
    def handle(self, *args, **options):
        print("This is an async task, so, if exists an error you must receivean email to {}".format(settings.ADMINS))
        task = course_index_monitoring.delay()
        return "Task id: {}".format(task.id)
