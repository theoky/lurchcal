# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
from CalendarOutlook import CalendarOutlook
from CalendarGoogle import CalendarGoogle
from Calendar import Calendar


class CalendarFactory:
    @staticmethod
    def create_calendar(calendar_type: str) -> Calendar:
        if calendar_type.lower() == "outlook":
            return CalendarOutlook()
        elif calendar_type.lower() == "google":
            return CalendarGoogle()
        else:
            raise ValueError(f"Unsupported calendar type: {calendar_type}")
