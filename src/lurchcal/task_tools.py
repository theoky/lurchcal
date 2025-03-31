# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

from kivy.logger import Logger


def flt_has_children(element):
    return element.has_children

def flt_ilm(element):
    return "ilm" in element.description.lower() or "ilm" in element.tags

def flt_contains_end_date_prio3(element):
    return element.due_date is not None and element.prio >= 3

def flt_contains_end_date_prio2(element):
    return element.due_date is not None and element.prio >= 2

def flt_contains_end_date_prio1(element):
    return element.due_date is not None and element.prio >= 1

def flt_contains_end_date(element):
    return element.due_date is not None

def flt_gte_prio3(element):
    return element.prio >= 3

def flt_prio2(element):
    return element.prio == 2

def flt_prio1(element):
    return element.prio == 1

def flt_contains_start_date(element):
    return element.start_date is not None

# def flt_is_in_future(element):
#     return "future" in element.tags

def filter_tasks(tasks, fits_criteria):
    elements_meeting_criteria = []
    elements_not_meeting_criteria = []

    for element in tasks:
        if fits_criteria(element):
            elements_meeting_criteria.append(element)
        else:
            elements_not_meeting_criteria.append(element)

    return elements_meeting_criteria, elements_not_meeting_criteria
