# -*- coding: utf-8 -*-
import json

from django.conf import settings
from django.contrib.auth.models import User

from student.models import CourseEnrollment
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.gating.api import get_entrance_exam_usage_key

from courseware import courses

from opaque_keys.edx.keys import CourseKey, UsageKey


class ServiceGrades(object):

    def __init__(self, course_id):
        course_key = CourseKey.from_string(course_id)
        self.course = courses.get_course_by_id(course_key)
        self.students = CourseEnrollment.objects.users_enrolled_in(course_key)

    def get_grades(self):
        course_grades = []
        for student in self.students:
            course_grade_factory = CourseGradeFactory().create(student, self.course)
            gradeset = course_grade_factory.summary
            gradeset["username"] = course_grade_factory.user
            gradeset["fullname"] = "{} {}".format(student.first_name, student.last_name)
            course_grades.append(gradeset)

        return course_grades

    def by_section(self):
        course_grade = self.get_grades()
        score_by_section = []
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            by_section = {}
            location_sections = []
            for section in sections.items():
                by_section["username"] = course_grade_factory.user.username
                score = course_grade_factory.score_for_chapter(section[0])
                location_sections.append({"name": section[1]["display_name"], "scores": score})
                by_section["sections"] = location_sections
            
            score_by_section.append(by_section)

        return score_by_section

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
