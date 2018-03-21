# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.contrib.auth.models import User

from student.models import CourseEnrollment
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from courseware import courses
from opaque_keys.edx.keys import CourseKey


def services_grade(course_id):
    course_key = CourseKey.from_string(course_id)
    course = courses.get_course_by_id(course_key)
    students = CourseEnrollment.objects.users_enrolled_in(course_key)

    course_grades = []
    for student in students:
        course_grade = CourseGradeFactory().create(student, course)
        gradeset = course_grade.summary
        gradeset["student"] = student.profile.name.title()
        gradeset["username"] = student.username
        course_grades.append(gradeset)

    return course_grades
