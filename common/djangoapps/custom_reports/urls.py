"""Defines the URL routes for reports API"""

from django.conf.urls import url
from django.conf import settings
from reports.api_views import WeeklyReport, MonthlyReport

# Regex pattern of uuid followed by .json or .csv
CSV_OR_JSON_FILE_PATTERN = r'(?P<csv_or_json_file_name>[0-9a-f]{8}\b-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-\b[0-9a-f]{12}[.](json|csv))'

urlpatterns = (
    url(r'^weekly_report_api/$', WeeklyReport.as_view()),
    url(r'^monthly_report_api/$', MonthlyReport.as_view()),
    url(r'^my_callback$', 'proversity.reports.views.my_callback'),
    url(r'^reports/{}$'.format(
        CSV_OR_JSON_FILE_PATTERN,
    ), 'proversity.reports.views.download_csv_or_json'),
)
