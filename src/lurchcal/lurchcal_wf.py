# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import logging
from copy import copy
from dataclasses import dataclass, field
from typing import Callable

from datetime import datetime, timedelta, date, time

from lurchcal.CalendarFactory import CalendarFactory

from bigtree import Node, find_name, preorder_iter

from lurchcal.TaskParser import TaskParser
from lurchcal.TaskScheduler import TaskScheduler
from lurchcal.settings import AppSettings, settings_from_config
from lurchcal.TaskServerClient import TaskServerClient

from lurchcal.task_tools import filter_tasks

logger = logging.getLogger(__name__)


def group_default_duration_appointments(scheduled_tasks, default_duration):
    """Merge adjacent default-duration scheduled tasks for calendar display."""
    grouped = []
    for item in sorted(scheduled_tasks, key=lambda scheduled: scheduled.start):
        task = item.task
        eligible = (
            task.is_default_duration
            and task.duration == default_duration
            and item.duration == default_duration
        )
        if grouped and eligible:
            previous = grouped[-1]
            previous_end = previous.start + timedelta(minutes=previous.duration)
            if (
                previous_end == item.start
                and hasattr(previous, "_grouped_default_tasks")
                and previous.task.tags == task.tags
                and previous.task.create_appt_anyway == task.create_appt_anyway
                and previous.task.block_time == task.block_time
            ):
                previous._grouped_default_tasks.append(task.description)
                previous.duration += item.duration
                previous.task.description = "\n".join(previous._grouped_default_tasks)
                continue
            if (
                previous_end == item.start
                and previous.task.is_default_duration
                and previous.task.duration == default_duration
                and previous.duration == default_duration
                and previous.task.tags == task.tags
                and previous.task.create_appt_anyway == task.create_appt_anyway
                and previous.task.block_time == task.block_time
            ):
                merged = copy(previous)
                merged.task = copy(previous.task)
                merged._grouped_default_tasks = [previous.task.description, task.description]
                merged.task.description = "\n".join(merged._grouped_default_tasks)
                merged.duration += item.duration
                grouped[-1] = merged
                continue
        grouped.append(item)
    return grouped

# globals

# TBD from ZIM?
# FUTURE_TAGS = []

# TBD Tags for Projects
# PROJECT_TAGS = ["project"]

def lurchcal():
    start_date = datetime(2023, 1, 12, 0, 0)
    days = 5

def print_appointments(date, appointments):
    """
    Prints a pretty printed list of appointments for a given date.

    Parameters:
        date (str): A string representing the date in the format 'YYYY-MM-DD'.
        appointments (list): A list of appointment strings.

    Returns:
        None
    """
    # Convert the date string to a datetime object.
    dt = datetime.strptime(date, "%Y-%m-%d")

    # Print the date and a header for the appointments.
    print(f"Appointments for {dt.strftime('%A, %B %d, %Y')}:\n")
    print("Time\t\tAppointment\n")

    # Sort the appointments by time.
    # appointments.sort()

    # Print each appointment with its time.
    for appt in appointments:
        print(f"{appt[:5]}\t\t{appt[6:]}\n")


def distribute_information(node, tags, topdown_duration):
    for n in node.children:
        t = n.get_attr("task")
        t.tags.extend(tags)

        if not t.is_default_duration:
            # set a new topdown_duration for if t has subtasks
            if t.assign_duration:
                topdown_duration = t.duration
            else:
                # default is distribute
                if n.children:
                    topdown_duration = int(t.duration / len(n.children) + 1)
        else:
            # t has a default duration but there is a duration from parent
            if topdown_duration:
                t.duration = topdown_duration

        distribute_information(n, t.tags, topdown_duration)


def build_tree(tasks):

    def parent_sort_key(task):
        """Keep numeric Zim IDs ordered while safely accepting string DTO IDs."""
        parent = task.parent
        try:
            return (0, int(parent))
        except (TypeError, ValueError):
            return (1, str(parent))

    ts = sorted(tasks, key=parent_sort_key)

    root = Node("0.0")
    for t in ts:
        id = str(t.id) + "." + str(t.subid)
        if not find_name(root, id):
            p = find_name(root, str(t.parent) + ".0")
            n = Node.from_dict({"name": id, "task": t})
            n.parent = p

    distribute_information(root, [], None)
    
    # TBD remove tasks with only subtasks -> may need modified sql statement

    return root


@dataclass
class WorkflowResult:
    scheduled_tasks: list = field(default_factory=list)
    unscheduled_tasks: list = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)


class SchedulingService:
    """UI-independent orchestration for scheduling and calendar actions."""

    def __init__(self, settings, calendar_factory=None, task_client_factory=None):
        self.settings = _coerce_settings(settings)
        self.calendar_factory = calendar_factory or CalendarFactory
        self.task_client_factory = task_client_factory or TaskServerClient

    def create_schedule(self, create_calendar_appointments=False, publish_schedule=True, progress=None):
        emit = progress or (lambda event: None)
        settings = self.settings
        emit({"stage": "tasks", "message": "Retrieving and parsing tasks"})
        task_server = self.task_client_factory(settings.task_server_url)
        tasks = TaskParser(settings).parse_tasks(task_server.get_tasks(date.today()+timedelta(days=settings.appt.days_for_scheduling)))
        task_tree = build_tree(tasks)
        tagged_task_list = [node.get_attr("task") for node in preorder_iter(
            task_tree, filter_condition=lambda x: x.node_name != "0.0")]
        ignored_tags = {tag.strip().casefold() for tag in settings.tags.tags_to_ignore if tag.strip()}
        if ignored_tags:
            tagged_task_list = [
                task for task in tagged_task_list
                if not ignored_tags.intersection(tag.casefold() for tag in task.tags)
            ]

        emit({"stage": "calendar", "message": "Reading calendar availability"})
        cal = self.calendar_factory.create_calendar(settings.appt.app)
        cal.authenticate()
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=settings.appt.days_for_scheduling)
        appointments = cal.get_appointments(start_date, end_date)

        emit({"stage": "scheduling", "message": "Scheduling tasks"})
        scheduled, unscheduled = TaskScheduler(settings).schedule_everything(
            cal, date.today(), tagged_task_list, appointments,
            start_time=datetime.now().time(), days=settings.appt.days_for_scheduling)

        emit({"stage": "calendar_update", "message": "Updating calendar appointments"})
        if create_calendar_appointments:
            delete_start = start_date - timedelta(days=settings.appt.days_for_scheduling)
            delete_end = start_date + timedelta(days=settings.appt.days_for_scheduling)
            cal.delete_lurchcal_meetings(cal.get_appointments(start_date, delete_end))
        for item in scheduled:
            if any(tag in item.task.tags for tag in settings.tags.tags_to_create_appt):
                item.task.create_appt_anyway = True
            if any(tag in item.task.tags for tag in settings.tags.tags_to_block_time):
                item.task.block_time = True
        appointment_candidates, _ = filter_tasks(
            scheduled,
            lambda item: (
                item.duration >= settings.appt.min_task_len_4_appt
                or any(tag in item.task.tags for tag in settings.tags.tags_to_create_appt)
                or (
                    item.task.is_default_duration
                    and item.task.duration == settings.tasks.def_task_len
                    and item.duration == settings.tasks.def_task_len
                )
            ),
        )
        if settings.create_grouped_private_appointments:
            grouped_candidates = group_default_duration_appointments(
                appointment_candidates, settings.tasks.def_task_len
            )
        else:
            grouped_candidates = appointment_candidates
        task_book = [
            item for item in grouped_candidates
            if (
                hasattr(item, "_grouped_default_tasks")
                or item.duration >= settings.appt.min_task_len_4_appt
                or any(tag in item.task.tags for tag in settings.tags.tags_to_create_appt)
            )
        ]
        if create_calendar_appointments:
            cal.create_appointments_4_tasks(task_book)

        if publish_schedule:
            emit({"stage": "publication", "message": "Publishing schedule"})
            task_server.publish_schedule(scheduled)
        result = WorkflowResult(scheduled, unscheduled, [], {
            "task_count": len(tagged_task_list), "scheduled_count": len(scheduled),
            "unscheduled_count": len(unscheduled), "appointment_count": len(task_book),
            "unscheduled_deadline_count": sum(
                task.due_date is not None for task in unscheduled
            ),
        })
        emit({"stage": "complete", "message": "Schedule completed", "statistics": result.statistics})
        return result

    def remove_calendar_appointments(self, progress=None):
        emit = progress or (lambda event: None)
        cal = self.calendar_factory.create_calendar(self.settings.appt.app)
        cal.authenticate()
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=self.settings.appt.days_for_scheduling)
        start -= timedelta(days=self.settings.appt.days_for_scheduling)
        cal.delete_lurchcal_meetings(cal.get_appointments(start, end))
        emit({"stage": "complete", "message": "LurchCal appointments removed"})


def _coerce_settings(settings):
    return settings if isinstance(settings, AppSettings) else settings_from_config(settings)
