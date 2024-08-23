# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""


class GenAppointment:

    def __init__(self) -> None:
        self.start_datetime = None
        self.end_datetime = None

        self.parsedDateTime_start = None
        self.parsedDateTime_end = None

        self.duration = 0  # in min
        self.summary = ""
        self.projects = ["DummyProject"]
        self.rel_day = None

        self.all_day_event = False

    def __str__(self) -> str:
        return "{}: {} - {}".format(
            self.summary, str(self.parsedDateTime_start), str(self.parsedDateTime_end)
        )
