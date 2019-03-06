from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_oauth.authentication import OAuth2Authentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import status
from ..utils import WeeklyReportGenerationThread, MonthlyReportGenerationThread, validate_parameters
from ..models import ReportsStatus
from .permissions import IsSuperuser
from django.core.exceptions import ValidationError


class AuthAPIView(APIView):
    authentication_classes = (OAuth2Authentication, SessionAuthentication)
    permission_classes = (IsSuperuser,)


class WeeklyReport(AuthAPIView):
    def post(self, request):
        try:
            course_ids, callback_url = validate_parameters(request)
        except ValueError as ve:
            return Response({
                "error": str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as error:
            error = error[0] if len(list(error)) > 0 else "Unknown error occured with Callback URL"
            return Response({
                "error": error
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            report_status = ReportsStatus.objects.get(status=1)
        except ReportsStatus.DoesNotExist:
            report_status = None

        if report_status:
            return Response({
                "message": "Report generation is already in process"
            })
        else:
            report_gen_thread = WeeklyReportGenerationThread(course_ids, callback_url)
            thread_id = report_gen_thread.get_id()
            report_gen_thread.start()
            return Response({
                "message": "Report generation started with id {}".format(thread_id)
            }, status=status.HTTP_202_ACCEPTED)


class MonthlyReport(AuthAPIView):
    def post(self, request):
        try:
            course_ids, callback_url = validate_parameters(request)
        except ValueError as ve:
            return Response({
                "error": str(ve)
            }, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as error:
            error = error[0] if len(list(error)) > 0 else "Unknown error occured with Callback URL"
            return Response({
                "error": error
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            report_status = ReportsStatus.objects.get(status=1)
        except ReportsStatus.DoesNotExist:
            report_status = None

        if report_status:
            response = {"message": "Report generation is already in process"}
            return Response(response)

        else:
            monthly_report_generation = MonthlyReportGenerationThread(course_ids, callback_url)
            thread_id = monthly_report_generation.get_id()
            monthly_report_generation.start()
            return Response({
                "message": "Report generation started with id {}".format(thread_id)
            }, status=status.HTTP_202_ACCEPTED)
