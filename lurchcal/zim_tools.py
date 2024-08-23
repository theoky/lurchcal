# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import sqlite3
from copy import deepcopy

from kivy.config import Config
from kivy.logger import Logger, LOG_LEVELS

from Task import Task


def read_ZIM_tasks(path_to_zim_db):
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


# TBD refactor -> class?
def parse_ZIM_tasks(path_to_zim_db, config, parsed_config):
    tasks = read_ZIM_tasks(path_to_zim_db)

    # parse all texts
    # _tag_re = re.compile(r'(?<!\S)@(\w+)\b', re.U)

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
                config.getint("tasks", "def_task_len"),
            )

            # split Tasks >1h into subtasks by creating tasks < 1h
            subid = 1
            while task.duration > config.getint("tasks", "min_task_split"):
                st = deepcopy(task)
                st.description = "st: " + task.description
                st.duration = config.getint("tasks", "min_task_split")
                st.subid = subid
                task.duration -= config.getint("tasks", "min_task_split")
                subid += 1

                res_tasks.append(st)

            # task to be scheduled
            res_tasks.append(task)

    return res_tasks