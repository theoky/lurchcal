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

# from outlook import get_calendar, get_appointments
from Calendar import Calendar
from CalendarGoogle import CalendarGoogle
from CalendarOutlook import CalendarOutlook

from bigtree import Node, find_name, preorder_iter

from outlook_enums import OlBusyStatus

from kivy.config import Config
from kivy.logger import Logger, LOG_LEVELS

from zim_tools import *

# globals

# TBD from ZIM?
# FUTURE_TAGS = []

# TBD Tags for Projects
# PROJECT_TAGS = ["project"]

def lurchcal():
    start_date = datetime(2023, 1, 12, 0, 0)
    days = 5


def get_next_day(d: date):
    res = d + timedelta(days=1)
    while res.isoweekday() >= 6:
        res = res + timedelta(days=1)

    return res


# def flt_is_in_future(element):
#     return "future" in element.tags


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


# filter for task
def flt_ilm(element):
    return "ilm" in element.description.lower() or "ilm" in element.tags


def flt_has_children(element):
    return element.has_children


def filter_tasks(tasks, fits_criteria):
    elements_meeting_criteria = []
    elements_not_meeting_criteria = []

    for element in tasks:
        if fits_criteria(element):
            elements_meeting_criteria.append(element)
        else:
            elements_not_meeting_criteria.append(element)

    return elements_meeting_criteria, elements_not_meeting_criteria


def schedule_tasks(days, tasks, start_date, end_date):
    Logger.debug("lurchal.py: schedule_tasks: {0} tasks".format(len(tasks)))

    ti = 0  # task_index
    res_scheduled_tasks = []
    not_scheduled_tasks = []

    while ti < len(tasks):
        cur_date = start_date
        task = tasks[ti]

        # start only after start date of task
        if task.start_date is not None and cur_date < task.start_date:
            if task.start_date > end_date:

                # task starts later, take next task
                ti += 1
                continue
            else:
                cur_date = task.start_date

        d = days[cur_date]
        do_schedule = True
        res = d.reserve_time(task.duration)

        while not res and do_schedule:
            cur_date = get_next_day(cur_date)
            if cur_date < end_date:
                d = days[cur_date]
                res = d.reserve_time(task.duration)

                # TODO do something with the reservation, so that an appointment can be made
            else:
                do_schedule = False

        if res:
            st = ScheduledTask(res[0], task, res[1])
            res_scheduled_tasks.append(st)

            # TODO check and log constraint violation

        else:
            # TODO log or exception
            not_scheduled_tasks.append(task)
            # print("can't schedule task any more: ", task.description)

        ti += 1

    return res_scheduled_tasks, not_scheduled_tasks


# https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
def daterange(start_date: date, end_date: date):
    days = int((end_date - start_date).days) + 1
    for n in range(days):
        yield start_date + timedelta(n)


def schedule_everything(
    cal, start_date, zim_tasks, appointments, config, parsed_config, start_time=None
):

    # prepare 7 days
    day_count = 7
    days = {}  #  dict[date, Day]
    act_start_date = None
    end_date = start_date + timedelta(days=7)

    # get work days from start date on
    first = True
    for single_date in (start_date + timedelta(n) for n in range(day_count)):
        if single_date.isoweekday() < 6:
            if not act_start_date:
                act_start_date = single_date

            days[single_date] = Day(
                single_date,
                parsed_config["start_of_day"],
                config.getint("appt", "hours_per_day"),
            )

            # block everything before now
            # ENH config
            if first:
                first = False

                if act_start_date == start_date:
                    n = datetime.now().time()
                    diff = datetime.combine(date.today(), n) - datetime.combine(
                        date.today(), time(0, 0)
                    )
                    diff_m = int(diff.total_seconds() / 60)

                    days[single_date].block_time(time(0, 0), diff_m)

    # first, schedule all calendar appointments for the next n days
    # TODO schedule calendar appointments
    for a in appointments:
        appt = cal.convert_appointment(a)

        if not appt:
            continue

        # ENH dsl?
        ignore = False
        for r in parsed_config["tag_ignore_appt"]:
            if re.search(r, appt.summary, re.IGNORECASE):
                ignore = True

        if ignore:
            continue

        # handle also multi day appointments
        for day in daterange(
            appt.parsedDateTime_start.date(), appt.parsedDateTime_end.date()
        ):
            d = days.get(day, None)
            if d:
                d.block_time(
                    time(
                        appt.parsedDateTime_start.hour, appt.parsedDateTime_start.minute
                    ),
                    appt.duration,
                )

    res_scheduled_tasks = []
    res_unscheduled_tasks = []

    # Schedule some Lunch
    # ENH refactor
    for d in days.values():
        lbt = parsed_config["lunch_break_time"]
        bnbt = parsed_config["before_noon_break_time"]
        d.block_time(lbt, config.getint("appt", "lunch_break"))
        d.block_time(bnbt, config.getint("appt", "short_break"))

        # show break as task if possible
        res_scheduled_tasks.append(
            ScheduledTask(
                datetime.combine(d.date, lbt),
                Task("Lunch"),
                config.getint("appt", "lunch_break"),
            )
        )
        res_scheduled_tasks.append(
            ScheduledTask(
                datetime.combine(d.date, bnbt),
                Task("Break"),
                config.getint("appt", "short_break"),
            )
        )

    # remove top hierarchy tasks
    zim_task_2schedule, remaining_zim_tasks = filter_tasks(zim_tasks, flt_has_children)

    # order by due asc, prio desc, start asc
    rows_sorted = multisort(
        remaining_zim_tasks,
        [
            mscol(
                "due_date", clean=lambda s: datetime(2999, 12, 31) if s is None else s
            ),
            mscol("prio", reverse=True),
            mscol("duration", reverse=True),
            mscol("start_date"),
        ],
    )

    Logger.debug(
        "schedule_everything.py: all tasks: {0} tasks".format(len(rows_sorted))
    )

    zim_future_tasks, remaining_zim_tasks = filter_tasks(
        rows_sorted,
        lambda t: any(e in t.tags for e in parsed_config["tags_future"]),
    )

    Logger.debug(
        "schedule_everything.py: tasks: {0}, future tasks: {1}".format(
            len(remaining_zim_tasks), len(zim_future_tasks)
        ),
    )

    # ENH add break after ILM
    if bool(config.getint("appt", "short_break_after_ilm")):
        pass

    # schedule all ILM tasks
    # schedule tasks with end date
    filter_list = [
        flt_ilm,
        flt_contains_end_date_prio3,
        flt_gte_prio3,
        flt_contains_end_date_prio2,
        flt_prio2,
        flt_contains_end_date_prio1,
        flt_prio1,
        flt_contains_end_date,
    ]

    Logger.debug("schedule_everything.py: schedule filtered tasks")
    for f in filter_list:
        zim_task_2schedule, remaining_zim_tasks = filter_tasks(remaining_zim_tasks, f)

        # add by specfied tag order
        rem_tasks = zim_task_2schedule
        for oot in parsed_config["tag_order"]:
            zt2s, rem_tasks = filter_tasks(rem_tasks, lambda e: oot in e.tags)

            rt, rut = schedule_tasks(days, zt2s, act_start_date, end_date)
            res_scheduled_tasks.extend(rt)
            res_unscheduled_tasks.extend(rut)

        rt, rut = schedule_tasks(days, rem_tasks, act_start_date, end_date)
        res_scheduled_tasks.extend(rt)
        res_unscheduled_tasks.extend(rut)

        # -- zim_task_2schedule is now scheduled

    # schedule the rest
    Logger.debug(
        "schedule_everything.py: schedule {0} remaining tasks".format(
            len(remaining_zim_tasks)
        )
    )
    rt, rut = schedule_tasks(days, remaining_zim_tasks, act_start_date, end_date)
    res_scheduled_tasks.extend(rt)
    res_unscheduled_tasks.extend(rut)

    # schedule future tasks (config) after all others if time left
    Logger.debug("schedule_everything.py: schedule future")
    rt, rut = schedule_tasks(days, zim_future_tasks, act_start_date, end_date)
    res_scheduled_tasks.extend(rt)
    res_unscheduled_tasks.extend(rut)

    return res_scheduled_tasks, res_unscheduled_tasks


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

    cal = CalendarOutlook()
    # cal = CalendarGoogle()
    cal.authenticate()

    # get ZIM tasks
    zim_tasks = parse_ZIM_tasks(zim_db, config, parsed_config)

    zim_task_tree = build_tree(zim_tasks)
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
    scheduled_tasks, unscheduled_tasks = schedule_everything(
        cal,
        date.today(),
        tagged_task_list,
        appointments,
        config,
        parsed_config,
        start_time=datetime.now().time(),
    )

    # sort scheduled tasks by date
    scheduled_tasks.sort(key=lambda x: x.start)

    # TBD date: print_appointments(date.today(), appointments)
    # print_appointments("2024-02-05", new_apps)

    # create appointments in calendar
    # print("Scheduled Tasks:")

    cb()

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
