# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
from durations_nlp import Duration

from datetime import datetime, time, date, timedelta
import re

tag_re = r"\@(\w+)"


class Task(object):
    def __init__(
        self,
        descr,
        prio=0,
        start_date=None,
        due_date=None,
        source_name="",
        has_children=False,
        id=0,
        parent=0,
        duration=6,
    ):
        self.prio = prio
        self.description = descr
        self.duration = duration
        self.is_default_duration = True
        self.assign_duration = False
        self.distribute_duration = True  # default

        self.source_name = source_name
        self.has_children = has_children
        self.tags = []
        self.id = id
        self.subid = 0
        self.parent = parent
        try:
            d = date.fromisoformat(due_date)
        except:
            d = None
        self.due_date = d

        try:
            d = date.fromisoformat(start_date)
        except:
            d = None
        self.start_date = d

        self.parse(descr)
        pass

    def parse(self, descr):
        d = descr.split("~")
        if len(d) >= 3:
            try:
                self.duration = Duration(d[1]).to_minutes()
                self.is_default_duration = False

                self.assign_duration = False
                self.distribute_duration = True

                if d[2]:
                    first_letter = d[2][0]
                    if first_letter == "a":
                        self.assign_duration = True
                        self.distribute_duration = False

            #                if first_letter == '~d' or d[2] =='~':

            except:
                pass
                # self.duration = 6.0

        m = re.findall(tag_re, descr, re.U)

        for t in m:
            self.tags.append(t.lower())

    # def __str__(self):
    #     return self.description + ", " + str(self.prio) + ", " + str(self.duration)

    def __str__(self):
        return f"description: {self.description}, start_date: {self.start_date}, prio: {self.prio}"

    def __repr__(self):
        return self.__str__()
