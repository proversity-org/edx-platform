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
from opaque_keys.edx.keys import CourseKey, UsageKey

from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from opaque_keys.edx.locator import CourseLocator, Locator, BlockLocatorBase

# from contentstore.views.helpers import get_parent_xblock, is_unit, xblock_type_display_name


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
        initial_header_rows = ['username']
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            section_dict = {}
            for section in sections.items():
                section_dict["username"] = course_grade_factory.user.username
                score = course_grade_factory.score_for_chapter(section[0])
                # Score object is a tuple: (earne, possible). We need only get earned value.
                # import ipdb; ipdb.set_trace()
                section_dict[section[1]["display_name"]] = score[0]
                initial_header_rows.append(section[1]["display_name"])

            score_by_section.append(section_dict)

        # We need to remove repeated values in this array, due to in the loop above
        # is repeated for each user
        header_rows = list(set(initial_header_rows))
        self.build_csv('section_report.csv', header_rows, score_by_section)

        return score_by_section

    def by_assignment_type(self):
        course_grade = self.get_grades()
        headers = ['username']
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            summary = course_grade_factory.graded_subsections_by_format

            for section in sections.items():
                chapter_name = section[1]['display_name']
                headers.append(chapter_name)
                sequentials = section[1]['sections']

                for sequential in sequentials:
                    headers.append('{} - {}'.format(chapter_name, sequential.format))
            
            results = {}
            results['username'] = student['username'].username

            for assignment_type in student["section_breakdown"]:
                if assignment_type.has_key('prominent') and assignment_type['prominent'] == True:
                    scores_list.append({assignment_type['category']: assignment_type['percent']})
                    results['assignment_type'] = scores_list
                    key = '{} - {}'.format(chapter_name, sequential.format)
                    results[key] = assignment_type['percent']

            assignment_type_grades.append(results)

        return assignment_type_grades

    def enhanced_problem_grade(self):
        course_grade = self.get_grades()
        headers = []
        rows = []
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            for section in sections.items():
                for sequentials in section[1]["sections"]:
                    scores = {}
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
