# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import os
import re

from datetime import datetime, timedelta, date, time
from dateutil import parser

from Task import Task
from Day import Day
from ScheduledTask import ScheduledTask
import definitions
from multisort import multisort, mscol

from Calendar import Calendar
from CalendarGoogle import CalendarGoogle
from CalendarOutlook import CalendarOutlook
from CalendarFactory import CalendarFactory

from bigtree import Node, find_name, preorder_iter

from outlook_enums import OlBusyStatus

from kivy.config import Config
from kivy.logger import Logger, LOG_LEVELS

from TaskParser import TaskParser
from TaskScheduler import TaskScheduler

from task_tools import filter_tasks

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

    ts = sorted(tasks, key=lambda x: x.parent)

    root = Node("0.0")
    for t in ts:
        id = str(t.id) + "." + str(t.subid)
        if not find_name(root, id):
            p = find_name(root, str(t.parent) + ".0")
            n = Node.from_dict({"name": id, "task": t})
            n.parent = p

    distribute_information(root, [], None)

    return root


def write_to_zim_page(zim_page, scheduled_tasks):
    cur_day = None
    with open(zim_page, mode="w", encoding="utf-8") as f:
        f.write("Content-Type: text/x-zim-wiki\n")
        f.write("Wiki-Format: zim 0.6\n")
        f.write("Creation-Date: " + datetime.now().isoformat())
        f.write("\n\n")

        f.write("====== Geplante Tasks ======\n")
        f.write("Created " + str(datetime.today()) + "\n\n")

        f.write("{} Tasks geplant.\n\n".format(len(scheduled_tasks)))

        for st in scheduled_tasks:
            if cur_day != st.start.date():
                cur_day = st.start.date()

                # TBD format date
                f.write("===== {} =====\n".format(str(cur_day)))

            tags = ", ".join(st.task.tags)

            f.write(
                "* {}, {}m, ({}): {} ({}), [[{}]]\n".format(
                    st.start,
                    st.duration,
                    st.task.prio,
                    st.task.description,
                    tags,
                    st.task.source_name,
                )
            )


def create_task_appointments(cb, create_appts, config, parsed_config):
    zim_db = config.get("zim", "path_db")  # os.environ.get("LURCHCAL_ZIM_DB")
    zim_page = config.get("zim", "path_page")  # os.environ.get("LURCHCAL_ZIM_PAGE")

    if not zim_db or not zim_page:
        raise RuntimeError("ZIM DB and/or page not found.")

    # Create calendar based on app setting in config
    app_type = config.get("appt", "app").lower()
    cal = CalendarFactory.create_calendar(app_type)
    
    cal.authenticate()

    # get ZIM tasks
    ## zim_tasks = parse_ZIM_tasks(zim_db, config, parsed_config)
    task_parser = TaskParser(config)
    tasks = task_parser.parse_zim_tasks(zim_db)

    zim_task_tree = build_tree(tasks) #zimtasks
    tagged_task_list = [
        node.get_attr("task")
        for node in preorder_iter(
            zim_task_tree, filter_condition=lambda x: x.node_name != "0.0"
        )
    ]

    cb()

    # get calendar appointments
    start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=config.getint("appt", "days_for_scheduling"))

    appointments = cal.get_appointments(start_date, end_date)

    cb()

    # schedule tasks
    scheduler = TaskScheduler(config, parsed_config)
    scheduled_tasks, unscheduled_tasks = scheduler.schedule_everything(
        cal,
        date.today(),
        tagged_task_list,
        appointments,
        start_time=datetime.now().time(),
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
            days=config.getint("appt", "days_for_scheduling")
        )
        start_delete_date = start_delete_date + timedelta(
            days=-config.getint("appt", "days_for_scheduling")
        )

        appointments_del_range = cal.get_appointments(start_date, end_date)
        cal.delete_lurchcal_meetings(appointments_del_range)

    cb()

    # add new appointments
    zim_task_book, remaining_zim_tasks = filter_tasks(
        scheduled_tasks,
        lambda t: t.duration >= config.getint("appt", "min_task_len_4_appt")
        or any(e in t.task.tags for e in parsed_config["tags_to_create_appt"]),
    )

    if create_appts:
        cal.create_appointments_4_tasks(zim_task_book)

    cb()

    write_to_zim_page(zim_page, scheduled_tasks)

    cb()
    return unscheduled_tasks
