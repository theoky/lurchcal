# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
Task parser for handling ZIM tasks and task descriptions.
"""
import re
import sqlite3
from copy import deepcopy
from durations_nlp import Duration

from kivy.config import Config
from kivy.logger import Logger, LOG_LEVELS

from Task import Task


class TaskParser:
    def __init__(self, config):
        self.config = config
        self.tag_re = r"\@(\w+)"
        
    def parse_zim_tasks(self, path_to_zim_db):
        tasks = self._read_zim_tasks(path_to_zim_db)
        return self._process_tasks(tasks)
        
        # parse all texts
        # _tag_re = re.compile(r'(?<!\S)@(\w+)\b', re.U)
    
    def parse_task_description(self, description):
        duration, is_default, assign_duration = self._parse_duration(description)
        tags = self._parse_tags(description)
        return duration, is_default, assign_duration, tags
        
    def _parse_duration(self, description):
        d = description.split("~")
        duration = self.config.getint("tasks", "def_task_len")
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

    def _read_zim_tasks(self, path_to_zim_db):
        condb = sqlite3.connect(path_to_zim_db)
        condb.row_factory = sqlite3.Row
        cursor = condb.cursor()

        # ( id INTEGER PRIMARY KEY,
        # source INTEGER,
        # parent INTEGER,
        # haschildren BOOLEAN,
        # hasopenchildren BOOLEAN,
        # status INTEGER,
        # prio INTEGER,
        # waiting BOOLEAN,
        # start TEXT,
        # due TEXT,
        # tags TEXT,
        # description TEXT )

        # get all tasks sorted by prio and date
        sql = """
            select tasklist.*, pages.name from tasklist 
            left join pages 
            on tasklist.source = pages.id
            where status = 0 and not waiting and start <= date()
            order by due asc, prio desc, start asc        
        """

        # select * from tasklist
        # where not haschildren and status = 0 and not waiting and start <= date()
        # where not haschildren and status = 0 and not waiting and start <= date()
        # order by due asc, prio desc
        ## TODO paramterize date()
        cursor.execute(sql)
        tasks = cursor.fetchall()
        condb.close()
        return tasks

    def _process_tasks(self, tasks):
        res_tasks = []

        for i, t in enumerate(tasks):
            d = t["description"]

            if not t["waiting"]:
                task = Task(
                    d,
                    t["prio"],
                    t["start"],
                    t["due"],
                    t["name"],
                    t["haschildren"],
                    t["id"],
                    t["parent"],
                    self.config.getint("tasks", "def_task_len"),
                )

                # split Tasks >1h into subtasks by creating tasks < 1h
                subid = 1
                while task.duration > self.config.getint("tasks", "min_task_split"):
                    st = deepcopy(task)
                    st.description = "st: " + task.description
                    st.duration = self.config.getint("tasks", "min_task_split")
                    st.subid = subid
                    task.duration -= self.config.getint("tasks", "min_task_split")
                    subid += 1

                    res_tasks.append(st)

                # task to be scheduled
                res_tasks.append(task)

        return res_tasks 