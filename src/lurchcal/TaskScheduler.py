# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
Task scheduler for managing task scheduling and calendar integration.
"""
import re
from datetime import datetime, timedelta, date, time

from kivy.logger import Logger

from lurchcal.Task import Task
from lurchcal.Day import Day
from lurchcal.ScheduledTask import ScheduledTask
from multisort import multisort, mscol

from lurchcal.task_tools import filter_tasks, flt_has_children, flt_ilm, flt_contains_end_date_prio3, \
    flt_contains_end_date_prio2, flt_contains_end_date_prio1, flt_contains_end_date, \
    flt_gte_prio3, flt_prio2, flt_prio1, flt_contains_start_date
    
class TaskScheduler:
    def __init__(self, config, parsed_config):
        self.config = config
        self.parsed_config = parsed_config
        self.days = {}
        
    def schedule_tasks(self, tasks, start_date, end_date):
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

            d = self.days[cur_date]
            do_schedule = True
            res = d.reserve_time(task.duration)

            while not res and do_schedule:
                cur_date = self._get_next_day(cur_date)
                if cur_date < end_date:
                    d = self.days[cur_date]
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
        
    def _prepare_days(self, start_date, end_date):
        day_count = (end_date - start_date).days
        self.days = {}  # dict[date, Day]
        act_start_date = None

        # get work days from start date on
        first = True
        for single_date in (start_date + timedelta(n) for n in range(day_count)):
            if single_date.isoweekday() < 6:
                if not act_start_date:
                    act_start_date = single_date

                self.days[single_date] = Day(
                    single_date,
                    self.parsed_config["start_of_day"],
                    self.config.getint("appt", "hours_per_day"),
                )

                # block everything before now
                # ENH config
                if first:
                    first = False
                    if act_start_date == start_date and act_start_date == date.today():
                        n = datetime.now().time()
                        diff = datetime.combine(date.today(), n) - datetime.combine(
                            date.today(), time(0, 0)
                        )
                        diff_m = int(diff.total_seconds() / 60)
                        self.days[single_date].block_time(time(0, 0), diff_m)
                        
        return act_start_date
        
    def _schedule_calendar_appointments(self, cal, appointments):
        for a in appointments:
            appt = cal.convert_appointment(a)

            if not appt:
                continue

            # ENH dsl?
            ignore = False
            for r in self.parsed_config["tag_ignore_appt"]:
                if re.search(r, appt.summary, re.IGNORECASE):
                    ignore = True
                    break

            if ignore:
                continue

            # handle also multi day appointments
            if appt.all_day_event:
                for day in self._daterange(
                    appt.parsedDateTime_start.date(), appt.parsedDateTime_end.date(), False
                ):
                    d = self.days.get(day, None)
                    if d:
                        d.block_time(
                            time(
                                appt.parsedDateTime_start.hour, appt.parsedDateTime_start.minute
                            ),
                            appt.duration,
                        )
        
    def _schedule_breaks(self):
        res_scheduled_tasks = []
        for d in self.days.values():
            lbt = self.parsed_config["lunch_break_time"]
            bnbt = self.parsed_config["before_noon_break_time"]
            d.block_time(lbt, self.config.getint("appt", "lunch_break"))
            d.block_time(bnbt, self.config.getint("appt", "short_break"))

            # show break as task if possible
            res_scheduled_tasks.append(
                ScheduledTask(
                    datetime.combine(d.date, lbt),
                    Task("Lunch"),
                    self.config.getint("appt", "lunch_break"),
                )
            )
            res_scheduled_tasks.append(
                ScheduledTask(
                    datetime.combine(d.date, bnbt),
                    Task("Break"),
                    self.config.getint("appt", "short_break"),
                )
            )
        return res_scheduled_tasks
        
    def _schedule_tasks_by_priority(self, tasks, start_date, end_date):
        res_scheduled_tasks = []
        res_unscheduled_tasks = []

        # remove top hierarchy tasks
        tasks_to_schedule, remaining_tasks = filter_tasks(tasks, flt_has_children)

        # order by due asc, prio desc, start asc
        rows_sorted = multisort(
            remaining_tasks,
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

        future_tasks, remaining_tasks = filter_tasks(
            rows_sorted,
            lambda t: any(e in t.tags for e in self.parsed_config["tags_future"]),
        )

        Logger.debug(
            "schedule_everything.py: tasks: {0}, future tasks: {1}".format(
                len(remaining_tasks), len(future_tasks)
            ),
        )

        # ENH add break after ILM
        # TBD right location?
        if bool(self.config.getint("appt", "short_break_after_ilm")):
            pass

        # schedule all ILM tasks and tasks with end date
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
            tasks_to_schedule, remaining_tasks = filter_tasks(remaining_tasks, f)

            # add by specified tag order
            rem_tasks = tasks_to_schedule
            for oot in self.parsed_config["tag_order"]:
                zt2s, rem_tasks = filter_tasks(rem_tasks, lambda e: oot in e.tags)
                rt, rut = self.schedule_tasks(zt2s, start_date, end_date)
                res_scheduled_tasks.extend(rt)
                res_unscheduled_tasks.extend(rut)

            rt, rut = self.schedule_tasks(rem_tasks, start_date, end_date)
            res_scheduled_tasks.extend(rt)
            res_unscheduled_tasks.extend(rut)

        # schedule the rest
        Logger.debug(
            "schedule_everything.py: schedule {0} remaining tasks".format(
                len(remaining_tasks)
            )
        )
        rt, rut = self.schedule_tasks(remaining_tasks, start_date, end_date)
        res_scheduled_tasks.extend(rt)
        res_unscheduled_tasks.extend(rut)

        # schedule future tasks after all others if time left
        Logger.debug("schedule_everything.py: schedule future")
        rt, rut = self.schedule_tasks(future_tasks, start_date, end_date)
        res_scheduled_tasks.extend(rt)
        res_unscheduled_tasks.extend(rut)

        return res_scheduled_tasks, res_unscheduled_tasks

    def _get_next_day(self, d: date):
        res = d + timedelta(days=1)
        while res.isoweekday() >= 6:
            res = res + timedelta(days=1)
        return res

    # https://stackoverflow.com/questions/1060279/iterating-through-a-range-of-dates-in-python
    def _daterange(self, start_date: date, end_date: date, incl=True):
        days = int((end_date - start_date).days)
        if incl:
            days += 1
            
        for n in range(days):
            yield start_date + timedelta(n)

    def schedule_everything(self, cal, start_date, tasks, appointments, start_time=None, days=5):
        end_date = start_date + timedelta(days=days)
        
        act_start_date = self._prepare_days(start_date, end_date)
        self._schedule_calendar_appointments(cal, appointments)
        res_scheduled_tasks = self._schedule_breaks()
        rt, rut = self._schedule_tasks_by_priority(tasks, act_start_date, end_date)
        res_scheduled_tasks.extend(rt)
        
        # sort scheduled tasks by date
        res_scheduled_tasks.sort(key=lambda x: x.start)
        
        return res_scheduled_tasks, rut 