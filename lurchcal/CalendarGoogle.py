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


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


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

    def simplify_appointments(self):
        if not self.events:
            return []

        for e in self.events:
            pass
