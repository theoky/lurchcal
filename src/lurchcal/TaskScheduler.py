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

from dateutil.rrule import rrule, rruleset, DAILY, WEEKLY, MONTHLY, MO, TU, WE, TH, FR, SA, SU
from dateutil.relativedelta import relativedelta
from copy import deepcopy

    
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
        day_count = 7
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

            if ignore:
                continue

            # handle also multi day appointments
            for day in self._daterange(
                appt.parsedDateTime_start.date(), appt.parsedDateTime_end.date()
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
    def _daterange(self, start_date: date, end_date: date):
        days = int((end_date - start_date).days) + 1
        for n in range(days):
            yield start_date + timedelta(n)

    def schedule_everything(self, cal, start_date, tasks, appointments, start_time=None):
        end_date = start_date + timedelta(days=7)
        
        act_start_date = self._prepare_days(start_date, end_date)
        self._schedule_calendar_appointments(cal, appointments)
        res_scheduled_tasks = self._schedule_breaks() # These are also tasks

        # Expand recurring tasks into instances
        expanded_tasks = []
        for task in tasks:
            if task.is_recurring:
                # Ensure scheduling_end_date for instance generation aligns with what _prepare_days and subsequent logic uses.
                # schedule_everything defines end_date as start_date + 7 days.
                # _prepare_days might adjust act_start_date but uses a 7-day range from original start_date for day creation.
                # Using 'end_date' from schedule_everything for consistency.
                instances = self._generate_recurrence_instances(task, act_start_date, end_date)
                expanded_tasks.extend(instances)
            else:
                expanded_tasks.append(task)
        
        # Now, schedule the expanded list of tasks (non-recurring + instances)
        rt, rut = self._schedule_tasks_by_priority(expanded_tasks, act_start_date, end_date)
        res_scheduled_tasks.extend(rt)
        
        # sort scheduled tasks by date
        res_scheduled_tasks.sort(key=lambda x: x.start)
        
        return res_scheduled_tasks, rut 

    def _generate_recurrence_instances(self, recurring_task: Task, scheduling_start_date: date, scheduling_end_date: date):
        instances = []
        if not recurring_task.is_recurring or not recurring_task.original_start_date:
            return instances

        rule_freq_map = {
            "daily": DAILY,
            "weekly": WEEKLY,
            "monthly": MONTHLY,
        }

        if recurring_task.recurrence_rule not in rule_freq_map:
            Logger.warning(f"Unsupported recurrence rule: {recurring_task.recurrence_rule} for task '{recurring_task.description}'")
            return instances

        freq = rule_freq_map[recurring_task.recurrence_rule]
        interval = recurring_task.recurrence_interval or 1
        dtstart = datetime.combine(recurring_task.original_start_date, time.min) # rrule needs datetime

        until_date = None
        if recurring_task.recurrence_end_date:
            until_date = datetime.combine(recurring_task.recurrence_end_date, time.max) # ensure it includes the whole day

        # rrule parameters
        kwargs = {
            'freq': freq,
            'interval': interval,
            'dtstart': dtstart,
            'count': recurring_task.recurrence_count,
            'until': until_date,
        }

        # Handling 'on' clause
        # For weekly: recurring_task.recurrence_on can be "MON", "TUE", etc.
        # For monthly: recurring_task.recurrence_on can be "15" (day of month), "last MON", "first TUE"
        
        weekday_map = {'MON': MO, 'TUE': TU, 'WED': WE, 'THU': TH, 'FRI': FR, 'SAT': SA, 'SUN': SU}

        if freq == WEEKLY and recurring_task.recurrence_on:
            if recurring_task.recurrence_on in weekday_map:
                kwargs['byweekday'] = [weekday_map[recurring_task.recurrence_on]]
            else: # Default to original start date's weekday if 'on' is invalid or not set
                 kwargs['byweekday'] = [weekday_map[recurring_task.original_start_date.strftime('%a').upper()[:3]]]


        elif freq == MONTHLY and recurring_task.recurrence_on:
            if recurring_task.recurrence_on.isdigit():
                kwargs['bymonthday'] = int(recurring_task.recurrence_on)
            else: # last/first weekday handling, e.g. "last FRI" or "first MON"
                parts = recurring_task.recurrence_on.split()
                if len(parts) == 2 and parts[0] in ['first', 'last'] and parts[1] in weekday_map:
                    num = 1 if parts[0] == 'first' else -1
                    weekday = weekday_map[parts[1]]
                    kwargs['byweekday'] = [weekday(num)] 
                # If not a digit and not a valid first/last weekday, default to original_start_date's day of month
                else:
                    kwargs['bymonthday'] = recurring_task.original_start_date.day


        # Generate dates using rrule
        # Note: rrule uses datetime objects
        try:
            generated_dates = list(rrule(**kwargs))
        except Exception as e:
            Logger.error(f"Error generating dates for task '{recurring_task.description}': {e}")
            return instances

        for dt_occurrence in generated_dates:
            occurrence_date = dt_occurrence.date()

            # Filter by scheduling window
            if occurrence_date < scheduling_start_date or occurrence_date > scheduling_end_date:
                continue

            instance = deepcopy(recurring_task)
            instance.start_date = occurrence_date
            # Assuming due_date is the same as start_date for instances of recurring tasks.
            # This might need adjustment if tasks can span multiple days or have specific due time logic.
            instance.due_date = occurrence_date 
            
            instance.is_recurring = False # Mark as not a template
            instance.recurrence_rule = None 
            instance.recurrence_interval = None
            instance.recurrence_on = None
            instance.recurrence_end_date = None
            instance.recurrence_count = None
            # instance.original_start_date remains the same as parent, could be useful for tracing.
            # Or set to None if it's purely an instance property: instance.original_start_date = None

            # Modify description to indicate it's a recurring instance
            instance.description = f"{recurring_task.description} [R]"
            
            instances.append(instance)
            
            # If count was the limiting factor, and we've generated enough, stop.
            # rrule already handles count, but this is a safeguard if we were to implement count manually.
            # if recurring_task.recurrence_count and len(instances) >= recurring_task.recurrence_count:
            #    break 
            # This check is actually handled by rrule's `count` parameter.

        return instances