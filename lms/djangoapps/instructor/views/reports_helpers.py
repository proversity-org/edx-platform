"""
Util functions and classes to build additional reports.
"""

# -*- coding: utf-8 -*-
from __future__ import division

from datetime import datetime
from time import time
from pytz import UTC

from lms.djangoapps.instructor_task.tasks_helper.utils import upload_csv_to_report_store


class DictList(dict):
    """
    Modify the behavior of a dict allowing has a list of values
    when there are more than one key with the same name.
    """
    def __setitem__(self, key, value):
        try:
            self[key]
        except KeyError:
            super(DictList, self).__setitem__(key, [])
        self[key].append(value)


def proccess_headers(headers):
    """
    Proccess duplicated values in header rows preserving the order.
    """
    seen = set()
    seen_add = seen.add
    return [item for item in headers if not (item in seen or seen_add(item))]


def proccess_grades_dict(grades_dict, counter_assignment_type):
    """
    Calculate grades taking into account the droppables.
    """
    for section, assignment_types in grades_dict.items():
        if isinstance(assignment_types, (list,)) and not section=='general_grade':
            group_grades = []
            for assignment_type in assignment_types:
                for name, grade in assignment_type.items():
                    total_number = counter_assignment_type[name]['total_number']
                    drop = counter_assignment_type[name]['drop']
                    average = grade / (total_number - drop)
                    group_grades.append(average)
            grades_dict.update({section: sum(group_grades)})
    return grades_dict.values()


def sum_dict_values(grades_dict, additional_items=None):
    """
    Since we have a list of grades in a key when a chapter has more than two subsequentials
    with the same assignment type, we need to sum these values and update the dict.
    """
    for key, value in grades_dict.items():
        if isinstance(value, (list,)):
            total = sum(value)
            if additional_items is not None:
                grades_dict.update(additional_items)
            grades_dict.update({key: total})
    return grades_dict


def order_list(sorted_list, elements):
    """
    Returns a list with the values of a dict based on a sorted list.

    Caveats:
        1. Items is sorted_list has to be present in the dict, this will be the keys.
        2. list and dict has to have the same lenght.

    Parameters:
        1. sorted_list: A list with the desired order.
        2. Dictionary

    Example:
        sorted_list = ['Item 1', 'Item 2', 'Item 3']
        elements = {'Item 2': 45, 'Item 1': 55, 'Item 3': 105}
        Wil return [55, 45, 105]
    """
    storage = []
    for header in header_rows:
        storage.append(element[header])
    return storage


def generate_csv(context, headers, rows, name):
    """
    Util function to generate CSV using ReportStore.

    Parameters:
        context: A _CourseGradeReportContext object
        headers: The headers for the csv
        rows: A list of lists with the values in the same order as headers, each list represent
        a new row in the csv.
    """
    date = datetime.now(UTC)
    context.update_status(u'Uploading grades')        
    upload_csv_to_report_store([headers] + rows, name, context.course_id, date)
    return context.update_status(u'Completed grades')
