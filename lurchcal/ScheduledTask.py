# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""


import Task


class ScheduledTask:

    def __init__(self, start=None, task=None, duration=0):
        self.start = start  # '2020-09-25 08:00'
        self.task = task
        self.duration = duration

    def __str__(self) -> str:
        return (
            str(self.start)
            + ", "
            + str(self.duration)
            + " m, "
            + self.task.description
            + ", von: "
            + self.task.source_name
        )
