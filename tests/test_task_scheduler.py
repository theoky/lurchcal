# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import unittest
from unittest.mock import Mock

import datetime as dt

from lurchcal.Task import Task
from lurchcal.TaskParser import TaskParser
from lurchcal.TaskScheduler import TaskScheduler
from lurchcal.GenAppointment import GenAppointment
from lurchcal.CalendarOutlook import CalendarOutlook
from lurchcal.outlook_enums import OlBusyStatus
from lurchcal.settings import AppSettings, AppointmentSettings, TaskSettings, TagSettings

from zoneinfo import ZoneInfo
import time_machine

at_tz = ZoneInfo("Europe/Vienna")

def make_scheduler_config():
    return AppSettings(
        appt=AppointmentSettings(15, 30, 15, 1, 7, dt.time(12), dt.time(10), dt.time(9), 8, 'outlook'),
        tasks=TaskSettings(30, 60),
        tags=TagSettings('ilm', ('priority1', 'priority2'), (), ('ignore_me',), ('appt',), ('future',), ('block',)),
    )

class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        # Create typed settings
        self.config = make_scheduler_config()

        self.scheduler = TaskScheduler(self.config)

    def test_initialization(self):
        """Test that TaskScheduler initializes correctly with config and parsed_config"""
        self.assertIsNotNone(self.scheduler.settings)
        self.assertEqual(self.scheduler.days, {})

    def test_prepare_days(self):
        """Test that days are prepared correctly with proper time blocks"""
        start_date = dt.date(2024, 1, 1)  # Monday
        end_date = dt.date(2024, 1, 7)    # Sunday

        act_start_date = self.scheduler._prepare_days(start_date, end_date)
        
        # Should have 5 workdays (Mon-Fri)
        self.assertEqual(len(self.scheduler.days), 5)
        self.assertEqual(act_start_date, start_date)
        
        # Check first day's time blocks
        first_day = self.scheduler.days[start_date]
        self.assertEqual(len(first_day.free_time_blocks), 1)
        self.assertEqual(first_day.free_time_blocks[0][1], 480)  # 8 hours in minutes


    def test_prepare_days_past(self):
        """Test that days are prepared correctly with proper time blocks"""
        start_date = dt.date(2024, 1, 1)  # Monday
        end_date = dt.date(2024, 1, 7)    # Sunday

        with time_machine.travel(dt.datetime(2024, 3, 30, 22, 0, 0, tzinfo=at_tz)):
            act_start_date = self.scheduler._prepare_days(start_date, end_date)
            
            # Should have 5 workdays (Mon-Fri)
            self.assertEqual(len(self.scheduler.days), 5)
            self.assertEqual(act_start_date, start_date)
            
            # Check first day's time blocks
            first_day = self.scheduler.days[start_date]
            self.assertEqual(len(first_day.free_time_blocks), 1)
            self.assertEqual(first_day.free_time_blocks[0][1], 480)  # 8 hours in minutes

    def test_prepare_days_cur(self):
        """Test that days are prepared correctly with proper time blocks"""
        start_date = dt.date(2025, 3, 31)  # Monday
        end_date = dt.date(2025, 4, 6)    # Sunday

        with time_machine.travel(dt.datetime(2025, 3, 31, 8, 0, 0, tzinfo=at_tz)):
            act_start_date = self.scheduler._prepare_days(start_date, end_date)
            
            # Should have 5 workdays (Mon-Fri)
            self.assertEqual(len(self.scheduler.days), 5)
            self.assertEqual(act_start_date, start_date)
            
            # Check first day's time blocks
            first_day = self.scheduler.days[start_date]
            self.assertEqual(len(first_day.free_time_blocks), 1)
            self.assertEqual(first_day.free_time_blocks[0][1], 480)  # 8 hours in minutes


    def test_prepare_days_latestart(self):
        """Test that days are prepared correctly with proper time blocks"""
        start_date = dt.date(2025, 3, 31)  # Monday
        end_date = dt.date(2025, 4, 6)    # Sunday

        with time_machine.travel(dt.datetime(2025, 3, 31, 10, 0, 0, tzinfo=at_tz)):
            act_start_date = self.scheduler._prepare_days(start_date, end_date)
            
            # Should have 5 workdays (Mon-Fri)
            self.assertEqual(len(self.scheduler.days), 5)
            self.assertEqual(act_start_date, start_date)
            
            # Check first day's time blocks
            first_day = self.scheduler.days[start_date]
            self.assertEqual(len(first_day.free_time_blocks), 1)
            self.assertEqual(first_day.free_time_blocks[0][1], 420)  # 7 hours in minutes


    def test_schedule_single_task(self):
        """Test scheduling a single task"""
        # Prepare days
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        # Create a test task
        task = Task("Test Task", prio=1, duration=60)  # 1 hour task

        # Schedule the task
        scheduled, unscheduled = self.scheduler.schedule_tasks([task], start_date, end_date)

        self.assertEqual(len(scheduled), 1)
        self.assertEqual(len(unscheduled), 0)
        self.assertEqual(scheduled[0].task.description, "Test Task")
        self.assertEqual(scheduled[0].duration, 60)

    def test_schedule_multiple_tasks(self):
        """Test scheduling multiple tasks with different priorities"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        tasks = [
            Task("High Priority", prio=3, duration=60),
            Task("Medium Priority", prio=2, duration=120),
            Task("Low Priority", prio=1, duration=60)
        ]

        scheduled, unscheduled = self.scheduler.schedule_tasks(tasks, start_date, end_date)

        self.assertEqual(len(scheduled), 3)
        self.assertEqual(len(unscheduled), 0)

    def test_schedule_breaks(self):
        """Test that breaks are scheduled correctly"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        scheduled_breaks = self.scheduler._schedule_breaks()

        # Should have 2 breaks per day (lunch and short break)
        self.assertEqual(len(scheduled_breaks), 10)  # 5 days * 2 breaks

        # Check first day's breaks
        first_day_breaks = [b for b in scheduled_breaks if b.start.date() == start_date]
        self.assertEqual(len(first_day_breaks), 2)
        self.assertEqual(first_day_breaks[0].task.description, "Lunch")
        self.assertEqual(first_day_breaks[1].task.description, "Break")

    def test_schedule_calendar_appointments(self):
        """Timed appointments block the overlapping portion of their day."""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        # Create a mock calendar appointment
        mock_appt = GenAppointment()
        mock_appt.summary = "Meeting"
        mock_appt.parsedDateTime_start = dt.datetime(2024, 1, 1, 10, 0)
        mock_appt.parsedDateTime_end = dt.datetime(2024, 1, 1, 11, 0)
        mock_appt.duration = 60
        mock_appt.all_day_event = False

        # Create a mock calendar
        mock_cal = Mock()
        mock_cal.convert_appointment.return_value = mock_appt

        self.scheduler._schedule_calendar_appointments(mock_cal, [mock_appt])

        first_day = self.scheduler.days[start_date]
        self.assertEqual(first_day.free_time(), 420)
        self.assertEqual(first_day.free_time_blocks[0][0], dt.datetime(2024, 1, 1, 9))
        self.assertEqual(first_day.free_time_blocks[1][0], dt.datetime(2024, 1, 1, 11))

    def test_multi_day_all_day_out_of_office_blocks_every_covered_workday(self):
        start_date = dt.date(2024, 1, 1)  # Monday
        self.scheduler._prepare_days(start_date, dt.date(2024, 1, 8))
        out_of_office = GenAppointment()
        out_of_office.summary = "Out of Office"
        out_of_office.parsedDateTime_start = dt.datetime(2024, 1, 2)
        # Calendar all-day event end dates are exclusive: Jan 2 through Jan 5.
        out_of_office.parsedDateTime_end = dt.datetime(2024, 1, 5)
        out_of_office.all_day_event = True

        calendar = Mock()
        calendar.convert_appointment.return_value = out_of_office
        self.scheduler._schedule_calendar_appointments(calendar, [out_of_office])

        for day in (dt.date(2024, 1, 2), dt.date(2024, 1, 3), dt.date(2024, 1, 4)):
            self.assertEqual(self.scheduler.days[day].free_time(), 0)
        self.assertGreater(self.scheduler.days[start_date].free_time(), 0)
        self.assertGreater(self.scheduler.days[dt.date(2024, 1, 5)].free_time(), 0)

    def test_timed_appointment_spanning_midnight_blocks_each_day_overlap(self):
        start_date = dt.date(2024, 1, 1)
        self.scheduler._prepare_days(start_date, dt.date(2024, 1, 8))
        appointment = GenAppointment()
        appointment.summary = "Overnight"
        appointment.parsedDateTime_start = dt.datetime(2024, 1, 2, 16)
        appointment.parsedDateTime_end = dt.datetime(2024, 1, 3, 10)
        appointment.all_day_event = False
        appointment.duration = 18 * 60

        calendar = Mock()
        calendar.convert_appointment.return_value = appointment
        self.scheduler._schedule_calendar_appointments(calendar, [appointment])

        self.assertEqual(self.scheduler.days[dt.date(2024, 1, 2)].free_time(), 420)
        self.assertEqual(self.scheduler.days[dt.date(2024, 1, 3)].free_time(), 420)
        self.assertEqual(
            self.scheduler.days[dt.date(2024, 1, 2)].free_time_blocks[0][0],
            dt.datetime(2024, 1, 2, 9),
        )
        self.assertEqual(
            self.scheduler.days[dt.date(2024, 1, 3)].free_time_blocks[0][0],
            dt.datetime(2024, 1, 3, 10),
        )

    def test_outlook_out_of_office_busy_status_is_retained(self):
        appointment = Mock()
        appointment.UserProperties.Find.return_value = None
        appointment.BusyStatus = OlBusyStatus.olOutOfOffice.value
        appointment.Subject = "Out of Office"
        appointment.Start = dt.datetime(2024, 1, 2)
        appointment.End = dt.datetime(2024, 1, 5)
        appointment.AllDayEvent = True
        appointment.Duration = 3 * 24 * 60

        converted = CalendarOutlook().convert_appointment(appointment)

        self.assertIsNotNone(converted)
        self.assertEqual(converted.parsedDateTime_start, appointment.Start)
        self.assertEqual(converted.parsedDateTime_end, appointment.End)

    def test_schedule_tasks_by_priority(self):
        """Test scheduling tasks with different priorities and tags"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        tasks = [
            Task("Priority 1 Task", prio=1, duration=60),
            Task("Priority 2 Task", prio=2, duration=60),
            Task("Priority 3 Task", prio=3, duration=60),
            Task("Future Task", prio=1, duration=60)
        ]
        tasks[-1].tags = ['future']  # Mark last task as future

        scheduled, unscheduled = self.scheduler._schedule_tasks_by_priority(tasks, start_date, end_date)

        self.assertEqual(len(scheduled), 4)
        self.assertEqual(len(unscheduled), 0)

    def test_unscheduled_tasks(self):
        """Test handling of tasks that can't be scheduled"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        # Create a task that's too long to fit
        task = Task("Long Task", prio=1, duration=1000)  # 16.67 hours

        scheduled, unscheduled = self.scheduler.schedule_tasks([task], start_date, end_date)

        self.assertEqual(len(scheduled), 0)
        self.assertEqual(len(unscheduled), 1)
        self.assertEqual(unscheduled[0].description, "Long Task")

    def test_task_with_start_date(self):
        """Test scheduling tasks with specific start dates"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        # Create a task that starts on Wednesday
        task = Task("Delayed Task", prio=1, duration=60, start_date="2024-01-03")

        scheduled, unscheduled = self.scheduler.schedule_tasks([task], start_date, end_date)

        self.assertEqual(len(scheduled), 1)
        self.assertEqual(len(unscheduled), 0)
        self.assertEqual(scheduled[0].start.date(), dt.date(2024, 1, 3))



def test_schedule_tasks_from_source_neutral_dtos():
    """High priority service DTO tasks schedule before lower priority work."""

    config = make_scheduler_config()
    scheduler = TaskScheduler(config)
    parser = TaskParser(config)
    tasks = parser.parse_tasks([
        {"id": "1", "parent_id": None, "description": "Long Focus Task ~2h~ @Deep",
         "priority": 3, "start_date": "2000-01-01", "due_date": "2024-01-02",
         "source_name": "Work", "has_children": False},
        {"id": "2", "parent_id": None, "description": "Write summary",
         "priority": 1, "start_date": "2000-01-01", "due_date": "2024-01-01",
         "source_name": "Work", "has_children": False},
    ])

    start_date = dt.date(2024, 1, 1)
    end_date = start_date + dt.timedelta(days=7)
    act_start_date = scheduler._prepare_days(start_date, end_date)

    scheduled, unscheduled = scheduler._schedule_tasks_by_priority(
        tasks, act_start_date, end_date
    )

    descriptions = [item.task.description for item in scheduled]
    assert descriptions == [
        "st: Long Focus Task ~2h~ @Deep",
        "Long Focus Task ~2h~ @Deep",
        "Write summary",
    ]

    start_times = [item.start.time() for item in scheduled]
    assert start_times == [dt.time(9, 0), dt.time(10, 0), dt.time(11, 0)]

    assert [item.task.duration for item in scheduled] == [60, 60, 30]
    assert [item.task.subid for item in scheduled] == [1, 0, 0]
    assert unscheduled == []

if __name__ == "__main__":
    unittest.main()
