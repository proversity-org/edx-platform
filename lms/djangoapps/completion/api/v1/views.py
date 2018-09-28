""" API v1 views. """
import csv
import logging
import copy

from celery.result import AsyncResult

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils.translation import ugettext as _
from django.http import HttpResponse, JsonResponse, Http404
from django.db import DatabaseError

from rest_framework_oauth.authentication import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import permissions
from rest_framework import status
from rest_framework.exceptions import ValidationError as API_ValidationError

from edx_rest_framework_extensions.authentication import JwtAuthentication
from opaque_keys.edx.keys import CourseKey, UsageKey
from opaque_keys import InvalidKeyError
from six import text_type

from lms.djangoapps.completion.models import BlockCompletion
from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.lib.api.permissions import IsStaffOrOwner
from student.models import CourseEnrollment
from completion import waffle
from lms.djangoapps.completion.utils import GenerateCompletionReport
from lms.djangoapps.completion.tasks import generate_report

logger = logging.getLogger(__name__)


class CompletionBatchView(APIView):
    """
    Handles API requests to submit batch completions.
    """
    permission_classes = (permissions.IsAuthenticated, IsStaffOrOwner,)
    REQUIRED_KEYS = ['username', 'course_key', 'blocks']

    def _validate_and_parse(self, batch_object):
        """
        Performs validation on the batch object to make sure it is in the proper format.

        Parameters:
            * batch_object: The data provided to a POST. The expected format is the following:
            {
                "username": "username",
                "course_key": "course-key",
                "blocks": {
                    "block_key1": 0.0,
                    "block_key2": 1.0,
                    "block_key3": 1.0,
                }
            }


        Return Value:
            * tuple: (User, CourseKey, List of tuples (UsageKey, completion_float)

        Raises:

            django.core.exceptions.ValidationError:
                If any aspect of validation fails a ValidationError is raised.

            ObjectDoesNotExist:
                If a database object cannot be found an ObjectDoesNotExist is raised.
        """
        if not waffle.waffle().is_enabled(waffle.ENABLE_COMPLETION_TRACKING):
            raise ValidationError(
                _("BlockCompletion.objects.submit_batch_completion should not be called when the feature is disabled.")
            )

        for key in self.REQUIRED_KEYS:
            if key not in batch_object:
                raise ValidationError(_("Key '{key}' not found.".format(key=key)))

        username = batch_object['username']
        user = User.objects.get(username=username)

        course_key = batch_object['course_key']
        try:
            course_key_obj = CourseKey.from_string(course_key)
        except InvalidKeyError:
            raise ValidationError(_("Invalid course key: {}").format(course_key))
        course_structure = CourseStructure.objects.get(course_id=course_key_obj)

        if not CourseEnrollment.is_enrolled(user, course_key_obj):
            raise ValidationError(_('User is not enrolled in course.'))

        blocks = batch_object['blocks']
        block_objs = []
        for block_key in blocks:
            if block_key not in course_structure.structure['blocks'].keys():
                raise ValidationError(_("Block with key: '{key}' is not in course {course}")
                                      .format(key=block_key, course=course_key))

            block_key_obj = UsageKey.from_string(block_key)
            completion = float(blocks[block_key])
            block_objs.append((block_key_obj, completion))

        return user, course_key_obj, block_objs

    def post(self, request, *args, **kwargs):
        """
        Inserts a batch of completions.

        REST Endpoint Format:
        {
          "username": "username",
          "course_key": "course-key",
          "blocks": {
            "block_key1": 0.0,
            "block_key2": 1.0,
            "block_key3": 1.0,
          }
        }

        **Returns**

        A Response object, with an appropriate status code.

        If successful, status code is 200.
        {
           "detail" : _("ok")
        }

        Otherwise, a 400 or 404 may be returned, and the "detail" content will explain the error.

        """
        batch_object = request.data or {}
        try:
            user, course_key, blocks = self._validate_and_parse(batch_object)
            BlockCompletion.objects.submit_batch_completion(user, course_key, blocks)
        except (ValidationError, ValueError) as exc:
            return Response({
                "detail": exc.message,
            }, status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist as exc:
            return Response({
                "detail": text_type(exc),
            }, status=status.HTTP_404_NOT_FOUND)
        except DatabaseError as exc:
            return Response({
                "detail": text_type(exc),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": _("ok")}, status=status.HTTP_200_OK)


class CompletionReportView(APIView):

    authentication_classes = (
        OAuth2Authentication,
        JwtAuthentication,
        SessionAuthentication
    )
    permission_classes = (permissions.IsAuthenticated, IsStaffOrOwner)

    def get(self, request, task_id):
        """
        This method returns a response value with the following structure

        if the task has been completed
        {
          "status": "Completed",
          "link": "report link",
          "result": [
            {'First Name': 'first name',
             'Last Name': 'last name',
             'Student Enrollment ID': user_id,
             'Email': email,
             'First Login': first login,
             'Last Login': last login,
             'Completed Activities': completed activities,
             'Total Activities': total activities,
             'Module Code': module code
             },
            {......},
            {......},
          ]
        }

        if the task has not been completed
        {
          "status": "Pending",
          "link": null,
          "result": []
        }

        """
        task = AsyncResult(id=task_id)
        result = None
        url = None

        if task.successful():
            # Extracting a deep copy of the result to prevent changing the object
            rows, url = copy.deepcopy(task.get())
            result = GenerateCompletionReport.serialize_rows(rows)

            if not url:
                url = reverse("completion_api:v1:download-completion-report", kwargs={"task_id": task.id})
        elif task.failed():
            result = task.info.message

        try:
            return JsonResponse(
                data={"status": task.status, "result": result, "link": url},
                status=status.HTTP_202_ACCEPTED,
            )
        except TypeError:
            raise Http404

    def post(self, request, course_id):
        """
        This method starts a celery task that generates a report with the information about
        the required activities and its state.
        Response format
            {
                "state_url": "/api/completion/v1/completion-report/YOUR_TASK_ID/status/"
            }
        """
        try:
            CourseKey.from_string(course_id)
        except InvalidKeyError:
            raise API_ValidationError(["The provided course id is not valid"])

        store_report = configuration_helpers.get_value("COMPLETION_STORAGE", False)
        task = generate_report.delay(course_id, store_report)
        state_url = reverse('completion_api:v1:completion-task-report', kwargs={"task_id": task.id})

        json_response = {
            "state_url": state_url
        }

        logger.info("StorageReport = %s", store_report)

        try:
            return JsonResponse(json_response, status=status.HTTP_200_OK)
        except TypeError:
            raise Http404


class DownloadReportView(APIView):

    authentication_classes = (
        OAuth2Authentication,
        JwtAuthentication,
        SessionAuthentication
    )
    permission_classes = (permissions.IsAuthenticated, IsStaffOrOwner)

    def get(self, request, task_id):
        task = AsyncResult(id=task_id)
        if task.ready():

            rows, url = task.result

            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="completion-report.csv"'
            response.write(u'\ufeff'.encode('utf8'))
            writer = csv.writer(response, dialect='excel')

            for row in rows:
                writer.writerow([field.encode('utf8') if isinstance(field, basestring) else field for field in row])

            return response

        raise Http404
