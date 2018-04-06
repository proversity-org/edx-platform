# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.contrib.auth.models import User

from student.models import CourseEnrollment
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from courseware import courses

from opaque_keys.edx.keys import CourseKey, UsageKey


class Dummy(object):

    def __init__(self):
        self.is_staff = True

    def user(self):
        return User.objects.get(username="staff").is_staff

    def is_staff(self):
        return True

    def has_user(self):
        return True


class ServiceGrades(object):

    def __init__(self, course_id):
        course_key = CourseKey.from_string(course_id)
        self.course = courses.get_course_by_id(course_key)
        self.students = CourseEnrollment.objects.users_enrolled_in(course_key)

    def get_grades(self):
        course_grades = []
        for student in self.students:
            course_grade = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade.summary
            sections = course_grade.chapter_grades
            gradeset["username"] = student.username
            gradeset["fullname"] = "{} {}".format(student.first_name, student.last_name)
            course_grades.append(gradeset)

        # We return a dict to access to these objects without iterate.
        response = {
            'course_grades': course_grades,
            'sections': sections
        }
        return response

    def by_section(self):
        gradeset = self.get_grades()
        grades = gradeset['course_grades']
        sections = gradeset['sections']        
        by_section = {}
    
        for grade in grades:
            by_section[grade["username"]] = {
                "fullname": grade["fullname"]
            }
            for section in grade["section_breakdown"]:
                if section.has_key('prominent'):
                    if section['prominent'] == True:
                        for chapter in sections.items():
                            section_name = chapter[1]['display_name']
                            by_section[grade["username"]].update({section_name: section['percent']})
        return by_section

    def by_assignment_type(self):
        gradeset = self.get_grades()
        by_section = {}
        for grade in gradeset:
            by_section[grade["username"]] = {
                "username": grade["username"],
                "grade": grade["percent"]
            }
            for section in grade["section_breakdown"]:
                by_section[grade["username"]].update({section["label"]: section["percent"] })
        return by_section
