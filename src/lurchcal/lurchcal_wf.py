# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import logging

from datetime import datetime, timedelta, date, time

from lurchcal.CalendarFactory import CalendarFactory

from bigtree import Node, find_name, preorder_iter

from lurchcal.TaskParser import TaskParser
from lurchcal.TaskScheduler import TaskScheduler
from lurchcal.settings import AppSettings, settings_from_config
from lurchcal.TaskServerClient import TaskServerClient

from lurchcal.task_tools import filter_tasks

logger = logging.getLogger(__name__)

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


def remove_appointments(cb, cal, settings):
    
    if not cal:
        app_type = settings.appt.app
        
        cal = CalendarFactory.create_calendar(app_type)
        cal.authenticate()

    # remove all appointments which are from lurchcal, so that they are not rescheduled
    start_delete_date = datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end_date = start_delete_date + timedelta(
        days=settings.appt.days_for_scheduling
    )
    start_delete_date = start_delete_date + timedelta(days=-settings.appt.days_for_scheduling)

    appointments_del_range = cal.get_appointments(start_delete_date, end_date)
    cal.delete_lurchcal_meetings(appointments_del_range)
    
    cb()


def create_task_appointments(cb, create_appts, settings):
    # Accept the Kivy ConfigParser during the transition from the UI boundary.
    settings = _coerce_settings(settings)
    # Create calendar based on app setting in config
    app_type = settings.appt.app
    
    # Retrieve source-neutral DTOs, then interpret/split them in LurchCal.
    logger.info("Retrieving tasks from Task Server")
    task_server = TaskServerClient(settings.task_server_url)
    task_parser = TaskParser(settings)
    tasks = task_parser.parse_tasks(task_server.get_tasks(date.today()))
    logger.info("Retrieved and parsed %d tasks", len(tasks))

    logger.info("Building task hierarchy")
    task_tree = build_tree(tasks)
    tagged_task_list = [
        node.get_attr("task")
        for node in preorder_iter(
            task_tree, filter_condition=lambda x: x.node_name != "0.0"
        )
    ]

    cb()

    cal = CalendarFactory.create_calendar(app_type)
    cal.authenticate()

    # get calendar appointments
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=settings.appt.days_for_scheduling)

    appointments = cal.get_appointments(start_date, end_date)

    cb()

    # schedule tasks
    logger.info("Scheduling %d tasks", len(tagged_task_list))
    scheduler = TaskScheduler(settings)
    scheduled_tasks, unscheduled_tasks = scheduler.schedule_everything(
        cal,
        date.today(),
        tagged_task_list,
        appointments,
        start_time=datetime.now().time(),
        days=settings.appt.days_for_scheduling
    )
    
    
    #   # schedule tasks
    # scheduled_tasks, unscheduled_tasks = schedule_everything(
    #     cal,
    #     date.today(),
    #     tagged_task_list,
    #     appointments,
    #     config,
    #     parsed_config,
    #     start_time=datetime.now().time(),
    # )

    # # sort scheduled tasks by date
    # scheduled_tasks.sort(key=lambda x: x.start)

    # # TBD date: print_appointments(date.today(), appointments)
    # # print_appointments("2024-02-05", new_apps)

    # # create appointments in calendar
    # # print("Scheduled Tasks:")

    cb()

    if create_appts:
        # remove all appointments which are from lurchcal, so that they are not rescheduled
        start_delete_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_date = start_delete_date + timedelta(
            days=settings.appt.days_for_scheduling
        )
        start_delete_date = start_delete_date + timedelta(
            days=-settings.appt.days_for_scheduling
        )

        appointments_del_range = cal.get_appointments(start_date, end_date)
        cal.delete_lurchcal_meetings(appointments_del_range)

    cb()

    for t in scheduled_tasks:
        if any(e in t.task.tags for e in settings.tags.tags_to_create_appt):
            t.task.create_appt_anyway = True
            
        if any(e in t.task.tags for e in settings.tags.tags_to_block_time):
            t.task.block_time = True
            
    # add new appointments
    task_book, remaining_tasks = filter_tasks(
        scheduled_tasks,
        lambda t: t.duration >= settings.appt.min_task_len_4_appt
        or any(e in t.task.tags for e in settings.tags.tags_to_create_appt),
    )

    if create_appts:
        logger.info("Creating calendar appointments for %d scheduled tasks", len(task_book))
        cal.create_appointments_4_tasks(task_book)

    cb()

    logger.info("Publishing schedule with %d tasks", len(scheduled_tasks))
    task_server.publish_schedule(scheduled_tasks)

    cb()
    return unscheduled_tasks


def _coerce_settings(settings):
    return settings if isinstance(settings, AppSettings) else settings_from_config(settings)
