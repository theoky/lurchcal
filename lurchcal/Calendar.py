# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

from abc import ABC, abstractmethod


class Calendar(ABC):

    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def get_appointments(self, begin, end):
        pass

    @abstractmethod
    def convert_appointment(self, appt):
        """Convert a calendar appointment to a simpler lurchal appointment.

        Args:
            appt (_type_): _description_

        Returns:
            _type_: _description_
        """
        return None

    @abstractmethod
    def create_appointments_4_tasks(self, scheduled_tasks):
        return None

    @abstractmethod
    def delete_lurchcal_meetings(self):
        return None
