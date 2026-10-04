# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""Interpret source-neutral task records as LurchCal scheduling tasks."""
import re
from copy import deepcopy
from durations_nlp import Duration

from lurchcal.Task import Task


class TaskParser:
    def __init__(self, settings):
        if not hasattr(settings, "tasks"):
            from lurchcal.settings import settings_from_config

            settings = settings_from_config(settings)
        self.settings = settings
        self.tag_re = r"\@(\w+)"

    def parse_tasks(self, task_records):
        """Convert Task Server DTO mappings to LurchCal Tasks and split as before."""
        return self._process_tasks(task_records)

    def parse_task_description(self, description):
        duration, is_default, assign_duration, _ = self._parse_duration(description)
        tags = self._parse_tags(description)
        return duration, is_default, assign_duration, tags

    def _parse_duration(self, description):
        d = description.split("~")
        duration = self.settings.tasks.def_task_len
        is_default = True
        assign_duration = False
        distribute_duration = True

        if len(d) >= 3:
            try:
                duration = Duration(d[1]).to_minutes()
                is_default = False

                if d[2]:
                    first_letter = d[2][0]
                    if first_letter == "a":
                        assign_duration = True
                        distribute_duration = False
            except:
                pass

        return duration, is_default, assign_duration, distribute_duration

    def _parse_tags(self, description):
        m = re.findall(self.tag_re, description, re.U)
        return [t.lower() for t in m]

    def _process_tasks(self, tasks):
        res_tasks = []

        for i, t in enumerate(tasks):
            d = t["description"]

            if not t.get("waiting", False):
                task = Task(
                    d,
                    t["priority"],
                    str(t["start_date"]) if t.get("start_date") else None,
                    str(t["due_date"]) if t.get("due_date") else None,
                    t.get("source_name") or "",
                    t["has_children"],
                    t["id"],
                    t.get("parent_id") or 0,
                    self.settings.tasks.def_task_len,
                )

                # split Tasks >1h into subtasks by creating tasks < 1h
                subid = 1
                while task.duration > self.settings.tasks.min_task_split:
                    st = deepcopy(task)
                    st.description = "st: " + task.description
                    st.duration = self.settings.tasks.min_task_split
                    st.subid = subid
                    task.duration -= self.settings.tasks.min_task_split
                    subid += 1

                    res_tasks.append(st)

                # task to be scheduled
                res_tasks.append(task)

        return res_tasks
