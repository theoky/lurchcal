# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import datetime
import os.path
from dateutil import parser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Calendar import Calendar
from GenAppointment import GenAppointment
from lurchcal import definitions

from kivy.logger import Logger

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class CalendarGoogle(Calendar):
    def __init__(self) -> None:
        self.creds = None
        self.events = []

    def authenticate(self):
        self.creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.

        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())

    def get_appointments(self, begin, end):
        try:
            service = build("calendar", "v3", credentials=self.creds)

            # Call the Calendar API
            begin_str = begin.isoformat() + "Z"
            end_str = end.isoformat() + "Z"

            # now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=begin_str,
                    timeMax=end_str,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            self.events = events_result.get("items", [])
            return self.events

        except HttpError as error:
            return []

        # print(f"An error occurred: {error}")
        # if not events:
        # TODO log print("No upcoming events found.")
        # return

    def isLurchCalAppt(self, appt):
        if appt:
            # Check if the event has extended properties
            if 'extendedProperties' in appt and 'private' in appt['extendedProperties']:
                # Check if our lurchcal property exists
                if 'lurchal' in appt['extendedProperties']['private']:
                    # Check if the value matches our GUID
                    if appt['extendedProperties']['private']['lurchal'] == definitions.LURCHCAL_GUID_TEST:
                        return True
        return False
    

    def convert_appointment(self, appt):
        ga = GenAppointment()
        ga.summary = appt["summary"].lower()

        ga.start_datetime = appt["start"].get("dateTime", appt["start"].get("date"))
        ga.parsedDateTime_start = parser.parse(ga.start_datetime)

        ga.end_datetime = appt["end"].get("dateTime", appt["end"].get("date"))
        ga.parsedDateTime_end = parser.parse(ga.end_datetime)

        ga.duration = (ga.parsedDateTime_end - ga.parsedDateTime_start).seconds / 60

        ga.rel_day = ga.parsedDateTime_start.date()
        return ga

    def create_appointments_4_tasks(self, scheduled_tasks):
        try:
            service = build("calendar", "v3", credentials=self.creds)
            
            batch = service.new_batch_http_request()
                        
            for st in scheduled_tasks:
                tags = ", ".join(st.task.tags)
                
                start_date = st.start
                end_date = start_date + datetime.timedelta(minutes=st.duration)
                
                # Format for Google Calendar API
                start_time = start_date.isoformat()
                end_time = end_date.isoformat()
                
                # Create event description
                description = (
                    f"Prio: {st.task.prio}\n"
                    + f"{st.task.description}\n"
                    + f"Source: {st.task.source_name} \n"
                )
                
                if tags:
                    description += f"Tags: {tags}"
                
                # Create the event
                event = {
                    'summary': st.task.description[:40],
                    'description': description,
                    'start': {
                        'dateTime': start_time,
                        'timeZone': 'Europe/Vienna',
                    },
                    'end': {
                        'dateTime': end_time,
                        'timeZone': 'Europe/Vienna',
                    },
                    'transparency': 'transparent',  # Equivalent to olFree in Outlook
                    'visibility': 'private',        # Equivalent to olPrivate in Outlook
                    'reminders': {
                        'useDefault': False,
                        'overrides': [],
                    },
                    # Add custom property similar to Outlook's lurchal property
                    'extendedProperties': {
                        'private': {
                            'lurchal': definitions.LURCHCAL_GUID_TEST
                        }
                    }
                }
                
                # Insert the event
                batch.add(
                        service.events().insert(calendarId='primary', body=event)
                    )
                
            batch.execute()
                
        except HttpError as error:
            Logger.error(f"An error occurred: {error}")
            
        return None

    def delete_lurchcal_meetings(self, appts):
        try:
            service = build("calendar", "v3", credentials=self.creds)
            
            # Collect event IDs for lurchcal appointments
            event_ids_to_delete = [
                event['id'] for event in appts if self.isLurchCalAppt(event)
            ]
            
            # Batch delete events
            if event_ids_to_delete:
                batch = service.new_batch_http_request()
                for event_id in event_ids_to_delete:
                    batch.add(
                        service.events().delete(calendarId='primary', eventId=event_id),
                        request_id=event_id
                    )
                batch.execute()
                Logger.info(f"Deleted {len(event_ids_to_delete)} lurchcal events.")
            else:
                Logger.info("No lurchcal events found to delete.")
                
        except HttpError as error:
            Logger.error(f"An error occurred while deleting events: {error}")
        
        return None
    
    def simplify_appointments(self):
        if not self.events:
            return []

        for e in self.events:
            pass
