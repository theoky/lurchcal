# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import win32com.client

from datetime import timedelta, datetime, timezone

from dateutil.parser import *

from Calendar import Calendar
from GenAppointment import GenAppointment

import definitions
from outlook_enums import *

from kivy.logger import Logger


class CalendarOutlook(Calendar):

    def __init__(self) -> None:
        self.outlook = None

    def authenticate(self):
        try:
            self.outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace(
                "MAPI"
            )

        except Exception as err:
            Logger.error("Outlook error, possibly not installed?", exc_info=err)
            raise

        return

    def get_appointments(self, begin, end):

        # begin = begin.astimezone(timezone.utc)
        # end = end.astimezone(timezone.utc)

        cal = self.outlook.GetDefaultFolder(9).Items
        cal.Sort("[Start]")
        cal.IncludeRecurrences = True

        # restriction1 = "[Start] >= '" + begin.strftime('%Y-%m-%d %H:%M %p') + "' AND [Start] <= '" + end.strftime('%Y-%m-%d %H:%M %p') + "'"
        restriction1 = (
            "[Start] >= '"
            + begin.strftime("%d.%m.%Y %I:%M %p")
            + "' AND [Start] <= '"
            + end.strftime("%d.%m.%Y %I:%M %p")
            + "'"
        )
        cal = cal.Restrict(restriction1)

        return cal

    def isLurchCalAppt(self, appt):
        if appt:
            lprop = appt.UserProperties.Find("lurchal", True)
            if lprop:
                # TBD
                if lprop.value == definitions.LURCHCAL_GUID_TEST:
                    return True
        return False

    def convert_appointment(self, appt):
        if self.isLurchCalAppt(appt):
            return None

        # TBD do also for Google
        if appt.BusyStatus in [
            OlBusyStatus.olTentative.value,
            OlBusyStatus.olWorkingElsewhere.value,
            OlBusyStatus.olFree.value,
        ]:
            return None

        ga = GenAppointment()
        ga.summary = appt.Subject.lower()

        ga.parsedDateTime_start = appt.Start
        ga.parsedDateTime_end = appt.End

        ga.all_day_event = appt.AllDayEvent
        ga.duration = appt.Duration

        Logger.debug(
            "CalendarOutlook.py: convert_appointment: {0}, {1}, {2}".format(
                ga.summary, ga.parsedDateTime_start, ga.parsedDateTime_end
            )
        )

        ga.rel_day = ga.parsedDateTime_start.date()

        return ga

    def create_appointment(self):
        return None

    def create_appointments_4_tasks(self, scheduled_tasks):

        cal = self.outlook.GetDefaultFolder(9).Items

        for st in scheduled_tasks:

            tags = ", ".join(st.task.tags)

            start_date = st.start
            end_date = start_date + timedelta(minutes=st.duration)

            s = start_date  # .astimezone(timezone.utc)
            e = end_date  # .astimezone(timezone.utc)

            sstr = s.strftime("%Y-%m-%d %H:%M %p")
            estr = e.strftime("%Y-%m-%d %H:%M %p")

            # https://learn.microsoft.com/en-us/office/vba/api/outlook.appointmentitem.reminderset
            appt = cal.Add()  # AppointmentItem
            appt.Start = sstr
            appt.Subject = st.task.description[:40]
            appt.Duration = st.duration

            b = (
                f"Prio: {st.task.prio}\n"
                + f"{st.task.description}\n"
                + f"Source: {st.task.source_name} \n"
            )

            if tags:
                b += f"Tags: {tags}"

            appt.Body = b

            appt.BusyStatus = OlBusyStatus.olFree.value
            appt.MeetingStatus = OlMeetingStatus.olNonMeeting.value
            appt.ReminderSet = False
            appt.Sensitivity = OlSensitivity.olPrivate.value

            prop = appt.UserProperties.Add("lurchal", OlUserPropertyType.olText.value)
            prop.Value = definitions.LURCHCAL_GUID_TEST

            appt.Save()

        return None

    def delete_lurchcal_meetings(self, appts):
        todelete = []
        for indx, a in enumerate(appts):
            if self.isLurchCalAppt(a):
                Logger.debug("processing {0}, {1}".format(str(a.Subject), str(a.Start)))
                todelete.append(indx + 1)

        if todelete:
            todelete.reverse()

            for i in todelete:
                Logger.debug("deleting {0}, {1}".format(i, str(appts.Item(i).Subject)))

                # make sure it is one of our appointments
                if self.isLurchCalAppt(appts.Item(i)):
                    appts.Item(i).Delete()
