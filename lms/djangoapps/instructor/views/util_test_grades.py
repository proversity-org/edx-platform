# -*- coding: utf-8 -*-
import csv
import json
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from pytz import UTC

from student.models import CourseEnrollment
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from courseware import courses
from opaque_keys.edx.keys import CourseKey


class ServiceGrades(object):

    def __init__(self, course_id):
        self.course_key = CourseKey.from_string(course_id)
        self.course = courses.get_course_by_id(self.course_key)
        self.students = CourseEnrollment.objects.users_enrolled_in(self.course_key)

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
        header_rows = ['username']
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            section_dict = {}
            for section in sections.items():
                section_dict["username"] = course_grade_factory.user.username
                score = course_grade_factory.score_for_chapter(section[0])
                # Score object is a tuple: (earned, possible). We need only get earned value.
                # import ipdb; ipdb.set_trace()
                section_dict[section[1]["display_name"]] = score[0]
                header_rows.append(section[1]["display_name"])

            score_by_section.append(section_dict)

        # We need to remove repeated values in this array, due to in the loop above
        # is repeated for each user
        header_rows = proccess_headers(header_rows)
        self.build_csv('section_report.csv', header_rows, score_by_section)

        return score_by_section

    def by_assignment_type(self):
        course_grade = self.get_grades()
        section_scores = self.by_section()
        headers = ['username']
        assignment_type_grades = []

        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            assignment_type_dict = {}

            for section in sections.items():
                assignment_type_dict['username'] = course_grade_factory.user.username
                chapter_name = section[1]['display_name']
                headers.append(chapter_name)
                sequentials = section[1]['sections']

                for sequential in sequentials:
                    key = '{} - {}'.format(chapter_name, sequential.format)
                    assignment_type_dict[key] = course_grade_factory.score_for_module(sequential.location)[0]
                    headers.append('{} - {}'.format(chapter_name, sequential.format))

            assignment_type_grades.append(assignment_type_dict)

        
        # Merge two list of dicts: Array of section grades using by_section method
        # and array of assignment type grades.
        for assignment_type in assignment_type_grades:
            for section in section_scores:
                if assignment_type['username'] == section['username']:
                    assignment_type.update(section)

        headers = proccess_headers(headers)
        self.build_csv('assignment_type_report.csv', headers, assignment_type_grades)

        return assignment_type_grades

    def enhanced_problem_grade(self):
        course_grade = self.get_grades()
        headers = []
        rows = []
        problem_scores = []
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            for section in sections.items():
                for sequentials in section[1]["sections"]:
                    scores = {}
                    # If a unit has more than one problem, we need to store it
                    # as a different object in the dict.
                    """
                    if len(sequentials.problem_scores) > 1:
                        for problem in sequentials.problem_scores.items():
                            key = "{} - {}".format(section[1]['display_name'], problem[0])
                            headers.append(key)
                            scores[key] = problem[1].earned
                            rows.append(scores)
                    """
                    for problem in sequentials.problem_scores.items():
                        key = "{} - {}".format(section[1]['display_name'], problem[0])
                        headers.append(key)
                        scores[key] = problem[1].earned
                        rows.append(scores)

        self.build_csv('enhanced_problem_grade.csv', headers, rows)
        return rows

    def build_csv(self, csv_name, header_rows, rows):
        """
        Construct the csv file.

        Arguments:
            csv_name: String for filename
            header_rows: List of values. e.g. ['username', 'section_name']
            rows : List of dicts. e.g [{'username': 'jhon', 'section_name': 'Introduction'}]

            Note that keys in rows argument must have the same names of the header_rows values.
        """

        # Proccess filename
        now = datetime.now(UTC)
        proccesed_date = now.strftime("%Y-%m-%d-%H%M")
        filename = "{}_{}_{}.csv".format(self.course_key, csv_name, proccesed_date)

        csv_file = open(filename, 'w')

        with csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header_rows)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        return csv_file


def proccess_headers(headers):
    return list(set(headers))