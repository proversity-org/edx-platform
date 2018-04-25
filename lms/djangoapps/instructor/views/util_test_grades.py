# -*- coding: utf-8 -*-
import csv
import json
from datetime import datetime
from collections import OrderedDict
from itertools import groupby
from operator import itemgetter


from django.conf import settings
from django.contrib.auth.models import User
from pytz import UTC

from student.models import CourseEnrollment

from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from lms.djangoapps.grades.new.course_grade import CourseGrade
from lms.djangoapps.grades.new.course_data import CourseData

from courseware import courses
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.grades.context import grading_context_for_course

from xmodule.modulestore.django import modulestore

# from common.lib.xmodule.xmodule.graders import AssignmentFormatGrader


class DictList(dict):
    """
    Modify the behavior of a dict allowing has a list of values
    when there are more than one same key.
    """
    def __setitem__(self, key, value):
        try:
            self[key].append(value) 
        except KeyError:
            super(DictList, self).__setitem__(key, value)
        except AttributeError:
            super(DictList, self).__setitem__(key, [self[key], value])


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
            course_grades.append(gradeset)

        return course_grades

    def by_section(self):
        course_grade = self.get_grades()
        score_by_section = []
        header_rows = ['username', 'general_grade', 'fullname']
        counter_assignment_type = {}
        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            course_data = CourseData(student, course=self.course)
            course_policy = course_data.course.grading_policy

            section_grade = DictList()
            section_grade['username'] = student['username'].username
            section_grade["fullname"] = student['username'].get_full_name()
            section_grade["general_grade"] = student['percent']

            for student_grade in student['section_breakdown']:
                # In graders constructor, we added some additional keys
                # in the section_breakdown json with the purpose to get the
                # subsection's parent and be able to differentiate when a grade is
                # calculated in a single entry. We apply this logic only if
                # has a subsection object and discard the droppables.
                if (student_grade.has_key('subsection') and
                    student_grade['subsection'] is not None or
                    student_grade.has_key('only') and not
                    student_grade.has_key('mark')):

                    # Get the parent of each sequential.
                    locator = student_grade['subsection'].location
                    parent = modulestore().get_parent_location(locator)
                    parent_location = modulestore().get_item(parent)

                    assignment_type = student_grade['subsection'].format

                    for policy in course_policy['GRADER']:
                        if policy['type'] == assignment_type:
                            grade = student_grade['percent'] * policy['weight']
                            chapter_name = parent_location.display_name
                            student_grade.update({'chapter_name': chapter_name})
                            # weight and grade keys are not mandatory neccesary in this dict,
                            # we added it just for keep tracked this information.
                            student_grade.update({'weight': policy['weight']})
                            student_grade.update({'grade': grade})
                            # We group in a list the values that has the same keys using DictList.
                            section_grade[chapter_name] = {assignment_type: grade}

                            counter_assignment_type[assignment_type] = policy['min_count']

                            header_rows.append(chapter_name)

            merged_grades = proccess_grades_dict(section_grade, counter_assignment_type)

            # Update the grades dict with the processed grades.
            section_grade.update(merged_grades)
            score_by_section.append(section_grade)

        # We need to remove repeated values in this array, due to in the loop above
        # is repeated for each user.
        header_rows = proccess_headers(header_rows)

        self.build_csv('section_report.csv', header_rows, score_by_section)
        return score_by_section

    def by_assignment_type(self):
        course_grade = self.get_grades()
        section_scores = self.by_section()
        headers = ['username', 'fullname']
        assignment_type_grades = []

        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            # In the case when a chapter has more than two subsequentials with the same assignment type
            # we need to store the grades in a list using DictList class.
            assignment_type_dict = DictList()
            assignment_type_dict['username'] = student['username'].username
            assignment_type_dict["fullname"] = student['username'].get_full_name()

            for section in sections.items():
                chapter_name = section[1]['display_name']
                headers.append(chapter_name)
                sequentials = section[1]['sections']

                for sequential in sequentials:
                    key = '{} - {}'.format(chapter_name, sequential.format)                    
                    assignment_type_dict[key] = course_grade_factory.score_for_module(sequential.location)[0]
                    headers.append('{} - {}'.format(chapter_name, sequential.format))

            # Since we have a list of grades in a key when a chapter has more than two subsequentials
            # with the same assignment type, we need to sum these values and update the dict.
            for key, value in assignment_type_dict.items():
                if isinstance(value, (list,)):
                    value = sum(value)
                    assignment_type_dict.update({key:value})

            assignment_type_grades.append(assignment_type_dict)

        # Merge two list of dicts: Array of section grades using by_section method
        # and array of assignment type grades.
        for assignment_type in assignment_type_grades:
            for section in section_scores:
                if assignment_type['username'] == section['username']:
                    # Using by_section object bring us general_grade key
                    # we need to delete it since is not neccesary in this report. 
                    del section['general_grade']
                    assignment_type.update(section)                    

        headers = proccess_headers(headers)
        # self.build_csv('assignment_type_report.csv', headers, assignment_type_grades)

        return assignment_type_grades

    def enhanced_problem_grade(self):
        course_grade = self.get_grades()
        headers = []
        rows = []
        grading_context = grading_context_for_course(self.course_key)

        for student in course_grade:
            course_grade_factory = CourseGradeFactory().create(student["username"], self.course)
            sections = course_grade_factory.chapter_grades
            problem_score_dict = {}
            problem_score_dict['username'] = student['username'].username
            problem_score_dict['fullname'] = student['username'].get_full_name()

            for section in sections.items():
                chapter_name = section[1]['display_name']
                sequentials = section[1]['sections']

                for sequential in sequentials:
                    for problem_score in sequential.problem_scores:
                        for problem_name in grading_context['all_graded_blocks']:
                            if problem_name.fields['category'] == 'problem':                                
                                if problem_name.location.block_id == problem_score.name:
                                    grade_tuple = course_grade_factory.score_for_module(problem_name.location)
                                    header_name = '{} - {} - {}'.format(chapter_name, sequential.display_name, problem_name.fields['display_name'])
                                    new_header = [header_name + " (Earned)", header_name + " (Possible)"]
                                    problem_score_dict[new_header[0]] = grade_tuple[0]
                                    problem_score_dict[new_header[1]] = grade_tuple[1]
                                    headers.append(new_header)

            rows.append(problem_score_dict)

        flatten_headers = [item for sublist in headers for item in sublist if sublist]
        headers = ['username', 'fullname'] + flatten_headers
        headers = proccess_headers(headers)

        self.build_csv('problem_grade_report.csv', headers, rows)
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
    """
    Proccess duplicated values in header rows preserving the order.
    """
    seen = set()
    seen_add = seen.add
    return [item for item in headers if not (item in seen or seen_add(item))]


def proccess_grades_dict(grades_dict, counter_assignment_type):
    new_grades_dict = {}
    for section, assignment_types in grades_dict.items():
        if isinstance(assignment_types, (list,)):
            group_dict = {}
            for assignment_type in assignment_types:
                for name, grade  in assignment_type.items():
                    group_dict[name] = group_dict.get(name, 0) + grade

            new_grades_dict[section] = group_dict

    for section, assignment_types_dict in new_grades_dict.items():
        assignment_type_list = new_grades_dict[section].keys()
        group_grades = []
        for item in assignment_type_list:
            average = new_grades_dict[section][item] / counter_assignment_type[item]
            group_grades.append(average)
        
        sum_grades = sum(group_grades)
        new_grades_dict.update({section: sum_grades})

    return new_grades_dict
