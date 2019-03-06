from threading import Thread
from grades.course_data import CourseData
from grades.course_grade import CourseGrade
from custom_reports.api import ENABLE_THREADING_IN_RG, TOTAL_THREADS_IN_WEEKLY_REPORT
from opaque_keys.edx.keys import CourseKey
from student.models import CourseEnrollment
from datetime import timedelta, date
from courseware import courses
from django.contrib.auth.models import User
from .models import ReportsStatus
import requests
import uuid, csv, json, math, copy
from api import REPORTS_DIR
from django.conf import settings
from django.core.validators import URLValidator
import logging

AUDIT_LOG = logging.getLogger("audit")

class CompletionCheckThread(Thread):
    def __init__(self, course, student):
        super(CompletionCheckThread, self).__init__()
        course_data = CourseData(student, course)
        self.course_grade = CourseGradeWithCompleted(student, course_data)
        self.student_id = student.id
        self.course_id = course.id
        self.result = {
            "student_id": self.student_id,
            "course_id": str(self.course_id),
        }

    def run(self):
        self.result['completed'] = self.course_grade.completed()


class CourseGradeWithCompleted(CourseGrade):
    def completed(self):
        for chapter in self.chapter_grades.itervalues():
            for subsection_grade in chapter['sections']:
                for key in subsection_grade.problem_scores:
                    if 'type@done' in str(key):
                        if subsection_grade.problem_scores[key].earned == 0:
                            return False
                    else:
                        if subsection_grade.problem_scores[key].first_attempted is None:
                            return False
        return True


class WeeklyReportGenerationThread(Thread):
    def __init__(self, course_ids, callback_url):
        super(WeeklyReportGenerationThread, self).__init__()
        self._id = str(uuid.uuid4())
        self.callback_url = callback_url
        self.course_keys = [
            CourseKey.from_string(course_id)
            for course_id in course_ids
        ]
        self.course_completion_user_list_fun = get_course_completion_user_list_threading if ENABLE_THREADING_IN_RG else get_course_completion_user_list

    def start(self):
        ReportsStatus.objects.create(jobid=self._id, status=1)
        super(WeeklyReportGenerationThread, self).start()

    def run(self):
        try:
            first_course_key = self.course_keys[0]

            course_completion_dict = self.course_completion_user_list_fun(self.course_keys)
            course_completion_count = get_course_completion_count(course_completion_dict)
            whole_programme_completed = get_programme_completion_count(course_completion_dict)

            context = {
                'users_on_programme': get_users_on_program_count(first_course_key),
                'new_user_seven_days': get_new_user_seven_days_count(first_course_key),
                'course_completion_count': course_completion_count,
                'whole_programme_completed': whole_programme_completed,
                'not_logged_in_30_days': get_not_logged_in_count(first_course_key, 30),
            }

            file_contents = json.dumps(context)

            with open('{}/{}.json'.format(REPORTS_DIR, self._id), 'wb') as json_file:
                json_file.write(file_contents)

            self.on_completed()
        except Exception as e:
            AUDIT_LOG.info("REPORTS_API: Report generation error - {}".format(e))
            ReportsStatus.objects.filter(jobid=self._id).update(status=3)

    def on_completed(self):
        ReportsStatus.objects.filter(jobid=self._id).update(result='{}.json'.format(self._id), status=2)
        file_http_path = "{}/{}{}/{}.json".format(settings.LMS_ROOT_URL, 'api/user-reports/', REPORTS_DIR, self._id)
        req_data = {
            "message": "JSON file is generated",
            "path": file_http_path
        }
        result = requests.post(self.callback_url, data=req_data)
        AUDIT_LOG.info("REPORTS_API: Webhook response sent to {} with data - {}".format(self.callback_url, json.dumps(req_data)))

    def get_id(self):
        return self._id


class MonthlyReportGenerationThread(Thread):
    def __init__(self, course_ids, callback_url):
        super(MonthlyReportGenerationThread, self).__init__()
        self._id = str(uuid.uuid4())
        self.callback_url = callback_url
        self.all_courses = [
            courses.get_course_by_id(CourseKey.from_string(course_id))
            for course_id in course_ids
        ]

    def start(self):
        ReportsStatus.objects.create(jobid=self._id, status=1)
        super(MonthlyReportGenerationThread, self).start()

    def run(self):
        try:
            users = User.objects.filter(is_staff=False, is_superuser=False).iterator()
            with open('{}/{}.csv'.format(REPORTS_DIR, self._id), 'wb') as csvfile:

                fieldnames = ['Username', 'Email', 'Full name', 'Account ID', 'Last Login Time']
                for course in self.all_courses:
                    fieldnames.append('{} ({})'.format(course.display_name, course.id))
                fieldnames.append("Programme")

                writer = csv.writer(csvfile)
                writer.writerow(fieldnames)
                for user in users:
                    write_row_for_monthly_report(user, self.all_courses, writer)
            self.on_completed()
        except Exception as e:
            AUDIT_LOG.info("REPORTS_API: Report generation error - {}".format(e))
            ReportsStatus.objects.filter(jobid=self._id).update(status=3)

    def on_completed(self):
        ReportsStatus.objects.filter(jobid=self._id).update(result='{}.csv'.format(self._id), status=2)
        file_http_path = "{}/{}{}/{}.csv".format(settings.LMS_ROOT_URL, 'api/user-reports/', REPORTS_DIR, self._id)
        req_data = {
            "message": "CSV file is generated",
            "path": file_http_path
        }
        result = requests.post(self.callback_url, data=req_data)
        AUDIT_LOG.info("REPORTS_API: Webhook response sent to {} with data - {}".format(self.callback_url, json.dumps(req_data)))

    def get_id(self):
        return self._id


def write_row_for_monthly_report(user, courses, writer):
    csv_row = [user.username, user.email, user.get_full_name(), user.username, user.last_login]
    lt_for_threads = []
    for course in courses:
        myth = CompletionCheckThread(course, user)
        lt_for_threads.append(myth)

    for th in lt_for_threads: th.start()
    for th in lt_for_threads: th.join()
    temp_res = []
    for th in lt_for_threads:
        temp_res.append(th.result['completed'])
        csv_row.append(yes_or_no(th.result['completed']))
    csv_row.append(yes_or_no(all(temp_res)))
    writer.writerow(csv_row)


def yes_or_no(bool_value):
    return 'Yes' if bool_value else 'No'


def get_intersection_count(list_of_lists):
    return len(set.intersection(*map(set, list_of_lists)))


def get_new_user_seven_days_count(course_key):
    start_date = date.today() - timedelta(days=7)
    enrolled_current = User.objects.filter(
        courseenrollment__course_id=course_key,
        courseenrollment__is_active=True,
        courseenrollment__created__gt=start_date
    )
    return len(enrolled_current)


def get_not_logged_in_count(course_key, days):
    date_before = date.today() - timedelta(days=days)
    enrolled_current = User.objects.filter(
        courseenrollment__course_id=course_key,
        courseenrollment__is_active=True,
        last_login__lt=date_before
    )
    return len(enrolled_current)


def get_users_on_program_count(course_key):
    course_enrollment_objs = CourseEnrollment.objects.filter(course_id=course_key, is_active=True)
    return len(course_enrollment_objs)


def get_course_completion_user_list(course_keys):
    course_completion_dict = {}
    for course_key in course_keys:
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=course_key,
            courseenrollment__is_active=1
        )
        course = courses.get_course_by_id(course_key)
        if str(course.id) not in course_completion_dict: course_completion_dict[str(course.id)] = {}
        if 'completed' not in course_completion_dict[str(course.id)]: course_completion_dict[str(course.id)][
            'completed'] = []
        course_completion_dict[str(course.id)]['course_name'] = course.display_name
        for student in enrolled_students:
            course_data = CourseData(student, course)
            course_grade = CourseGradeWithCompleted(student, course_data)
            if course_grade.completed():
                course_completion_dict[str(course.id)]['completed'].append(student.id)
    return course_completion_dict


def get_course_completion_user_list_threading(course_keys):
    lt_for_threads = []
    course_completion_dict = {}
    for course_key in course_keys:
        enrolled_students = User.objects.filter(
            courseenrollment__course_id=course_key,
            courseenrollment__is_active=1
        )
        course = courses.get_course_by_id(course_key)
        if str(course.id) not in course_completion_dict: course_completion_dict[str(course.id)] = {}
        course_completion_dict[str(course.id)]['course_name'] = course.display_name
        for student in enrolled_students:
            lt_for_threads.append(CompletionCheckThread(course, student))

    total_threads = TOTAL_THREADS_IN_WEEKLY_REPORT

    if total_threads < len(lt_for_threads):
        for i in range(int(math.ceil(float(len(lt_for_threads)) / total_threads))):
            for j in range(total_threads):
                if total_threads * i + j < len(lt_for_threads): lt_for_threads[total_threads * i + j].start()
            for j in range(total_threads):
                if total_threads * i + j < len(lt_for_threads): lt_for_threads[total_threads * i + j].join()
    else:
        for th in lt_for_threads: th.start()
        for th in lt_for_threads: th.join()

    for th in lt_for_threads:
        if th.result['course_id'] not in course_completion_dict: course_completion_dict[th.result['course_id']] = {}
        if 'completed' not in course_completion_dict[th.result['course_id']]:
            course_completion_dict[th.result['course_id']]['completed'] = []
        if th.result['completed']:
            course_completion_dict[th.result['course_id']]['completed'].append(th.result['student_id'])
    return course_completion_dict


def validate_parameters(request):
    if ('course_ids' not in request.data) or ('callback_url' not in request.data):
        raise ValueError("insufficient parameters")

    course_ids = request.data['course_ids']
    if type(course_ids) is not list:
        raise ValueError("course_ids is not an array")

    callback_url = request.data['callback_url']
    for i in course_ids:
        courses.get_course(CourseKey.from_string(i))

    validate_url = URLValidator()
    validate_url(callback_url)
    return course_ids, callback_url


def get_course_completion_count(result_dict):
    result_dict = copy.deepcopy(result_dict)
    for key in result_dict:
        result_dict[key]['completed'] = len(result_dict[key]['completed'])
        result_dict[key]['course_id'] = key
    return result_dict.values()


def get_programme_completion_count(result_dict):
    return get_intersection_count([
        result_dict[key]['completed']
        for key in result_dict
    ])
