# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import unittest
from unittest.mock import Mock, patch

import datetime as dt
import time # so we can override time.time

from kivy.config import ConfigParser 

from lurchcal.Task import Task
from lurchcal.TaskScheduler import TaskScheduler
from lurchcal.GenAppointment import GenAppointment

from zoneinfo import ZoneInfo
import time_machine

at_tz = ZoneInfo("Europe/Vienna")

mock_time = Mock()
mock_time.return_value = time.mktime(dt.datetime(2024, 3, 31, 22, 6).timetuple())

class TestTaskScheduler(unittest.TestCase):
    def setUp(self):
        # Create a mock config
        self.config = ConfigParser()
        self.config.add_section('appt')
        self.config.set('appt', 'hours_per_day', '8')
        self.config.set('appt', 'lunch_break', '30')
        self.config.set('appt', 'short_break', '15')
        self.config.set('appt', 'short_break_after_ilm', '1')
        self.config.set('appt', 'days_for_scheduling', '7')
        self.config.set('appt', 'min_task_len_4_appt', '15')

        # Create parsed config
        self.parsed_config = {
            'start_of_day': dt.time(9, 0),
            'lunch_break_time': dt.time(12, 0),
            'before_noon_break_time': dt.time(10, 0),
            'tag_order': ['priority1', 'priority2'],
            'tag_ignore_appt': ['ignore_me'],
            'tags_future': ['future'],
            'tags_to_create_appt': ['appt']
        }

        self.scheduler = TaskScheduler(self.config, self.parsed_config)

    def test_initialization(self):
        """Test that TaskScheduler initializes correctly with config and parsed_config"""
        self.assertIsNotNone(self.scheduler.config)
        self.assertIsNotNone(self.scheduler.parsed_config)
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
        """Test scheduling around calendar appointments"""
        start_date = dt.date(2024, 1, 1)
        end_date = dt.date(2024, 1, 7)
        self.scheduler._prepare_days(start_date, end_date)

        # Create a mock calendar appointment
        mock_appt = GenAppointment()
        mock_appt.summary = "Meeting"
        mock_appt.parsedDateTime_start = dt.datetime(2024, 1, 1, 10, 0)
        mock_appt.parsedDateTime_end = dt.datetime(2024, 1, 1, 11, 0)
        mock_appt.duration = 60

        # Create a mock calendar
        mock_cal = Mock()
        mock_cal.convert_appointment.return_value = mock_appt

        self.scheduler._schedule_calendar_appointments(mock_cal, [mock_appt])

        # Check that the time is blocked
        first_day = self.scheduler.days[start_date]
        self.assertEqual(len(first_day.free_time_blocks), 2)  # Should be split into two blocks

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


class TestRecurrenceGeneration(unittest.TestCase):
    def setUp(self):
        self.config = ConfigParser() 
        self.config.add_section('appt')
        self.config.set('appt', 'hours_per_day', '8') 
        self.config.set('appt', 'lunch_break', '30') # Required by _schedule_breaks
        self.config.set('appt', 'short_break', '15') # Required by _schedule_breaks
        self.config.set('appt', 'days_for_scheduling', '7') # Required by schedule_everything internal logic
        # Add other minimal required settings if any more errors pop up
        # self.config.set('appt', 'short_break_after_ilm', '1') # Not strictly needed for this test path
        # self.config.set('appt', 'min_task_len_4_appt', '15') # Not strictly needed for this test path


        self.parsed_config = { # Basic parsed_config
            'start_of_day': dt.time(9, 0), 
            'lunch_break_time': dt.time(12,0), 
            'before_noon_break_time': dt.time(10,0),
            # Add other minimal required settings if any more errors pop up
            'tag_order': [], 
            'tag_ignore_appt': [],
            'tags_future': [],
            'tags_to_create_appt': []
        }
        self.scheduler = TaskScheduler(self.config, self.parsed_config)
        self.scheduling_start_date = dt.date(2024, 1, 1)
        self.scheduling_end_date = dt.date(2024, 3, 31)

    def _create_base_task(self, description="Recurring Task", original_start_str="2024-01-01"):
        task = Task(description, prio=1, duration=60, start_date=original_start_str)
        task.is_recurring = True
        task.original_start_date = dt.date.fromisoformat(original_start_str)
        return task

    def test_generate_daily_instances_simple(self):
        task = self._create_base_task()
        task.recurrence_rule = "daily"
        
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, dt.date(2024, 1, 5))
        self.assertEqual(len(instances), 5)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 1))
        self.assertEqual(instances[4].start_date, dt.date(2024, 1, 5))
        self.assertFalse(instances[0].is_recurring)
        self.assertEqual(instances[0].description, "Recurring Task [R]")

    def test_generate_daily_instances_with_interval(self):
        task = self._create_base_task()
        task.recurrence_rule = "daily"
        task.recurrence_interval = 2
        
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, dt.date(2024, 1, 7))
        self.assertEqual(len(instances), 4) # Jan 1, 3, 5, 7
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 1))
        self.assertEqual(instances[1].start_date, dt.date(2024, 1, 3))

    def test_generate_daily_instances_with_count(self):
        task = self._create_base_task()
        task.recurrence_rule = "daily"
        task.recurrence_count = 3
        
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, self.scheduling_end_date)
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[2].start_date, dt.date(2024, 1, 3))

    def test_generate_daily_instances_with_until(self):
        task = self._create_base_task()
        task.recurrence_rule = "daily"
        task.recurrence_end_date = dt.date(2024, 1, 4)
        
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, self.scheduling_end_date)
        self.assertEqual(len(instances), 4) # Jan 1, 2, 3, 4
        self.assertEqual(instances[-1].start_date, dt.date(2024, 1, 4))

    def test_generate_weekly_instances_simple(self):
        # Starts on Monday 2024-01-01
        task = self._create_base_task(original_start_str="2024-01-01") 
        task.recurrence_rule = "weekly"
        
        # Schedule for 3 weeks
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 1, 21))
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 1)) # Mon
        self.assertEqual(instances[1].start_date, dt.date(2024, 1, 8)) # Mon
        self.assertEqual(instances[2].start_date, dt.date(2024, 1, 15)) # Mon

    def test_generate_weekly_instances_on_specific_day(self):
        task = self._create_base_task(original_start_str="2024-01-01") # Monday
        task.recurrence_rule = "weekly"
        task.recurrence_on = "WED" # Should generate Wednesdays
        
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 1, 21))
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 3)) # First WED
        self.assertEqual(instances[1].start_date, dt.date(2024, 1, 10))
        self.assertEqual(instances[2].start_date, dt.date(2024, 1, 17))

    def test_generate_weekly_instances_interval_count_until(self):
        task = self._create_base_task(original_start_str="2024-01-01") # Monday
        task.recurrence_rule = "weekly"
        task.recurrence_interval = 2 # Every 2 weeks
        task.recurrence_on = "FRI"
        task.recurrence_count = 2 
        
        # Window large enough not to interfere with count
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 2, 28)) 
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 5)) # First Friday
        self.assertEqual(instances[1].start_date, dt.date(2024, 1, 19)) # Second Friday (2 weeks after 1st Fri)

        task.recurrence_count = None
        task.recurrence_end_date = dt.date(2024, 1, 20)
        instances_until = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 2, 28))
        self.assertEqual(len(instances_until), 2) # Jan 5, Jan 19. Jan 20 is a Saturday.
        self.assertEqual(instances_until[0].start_date, dt.date(2024, 1, 5))
        self.assertEqual(instances_until[1].start_date, dt.date(2024, 1, 19))


    def test_generate_monthly_instances_day_number(self):
        task = self._create_base_task(original_start_str="2024-01-10")
        task.recurrence_rule = "monthly"
        task.recurrence_on = "15" # 15th of every month
        
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 3, 31))
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 15))
        self.assertEqual(instances[1].start_date, dt.date(2024, 2, 15))
        self.assertEqual(instances[2].start_date, dt.date(2024, 3, 15))

    def test_generate_monthly_instances_first_weekday(self):
        task = self._create_base_task(original_start_str="2024-01-01")
        task.recurrence_rule = "monthly"
        task.recurrence_on = "first MON"
        
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 3, 31))
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 1)) # Jan 1 is Mon
        self.assertEqual(instances[1].start_date, dt.date(2024, 2, 5)) # First Mon in Feb
        self.assertEqual(instances[2].start_date, dt.date(2024, 3, 4)) # First Mon in Mar

    def test_generate_monthly_instances_last_weekday(self):
        task = self._create_base_task(original_start_str="2024-01-01")
        task.recurrence_rule = "monthly"
        task.recurrence_on = "last FRI"
        task.recurrence_count = 2
        
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024, 1, 1), dt.date(2024, 3, 31))
        self.assertEqual(len(instances), 2)
        self.assertEqual(instances[0].start_date, dt.date(2024, 1, 26)) # Last Fri in Jan
        self.assertEqual(instances[1].start_date, dt.date(2024, 2, 23)) # Last Fri in Feb (29th is Thu)

    def test_instance_properties_and_non_recursion(self):
        task = self._create_base_task(description="Test Desc", original_start_str="2024-01-01")
        task.recurrence_rule = "daily"
        task.recurrence_count = 1
        task.tags = ["test", "important"]
        
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, self.scheduling_end_date)
        self.assertEqual(len(instances), 1)
        instance = instances[0]
        
        self.assertEqual(instance.description, "Test Desc [R]")
        self.assertEqual(instance.prio, 1)
        self.assertEqual(instance.duration, 60)
        self.assertIn("test", instance.tags)
        self.assertIn("important", instance.tags)
        
        self.assertFalse(instance.is_recurring)
        self.assertIsNone(instance.recurrence_rule)
        self.assertEqual(instance.start_date, dt.date(2024, 1, 1))
        self.assertEqual(instance.due_date, dt.date(2024, 1, 1)) # As per current implementation

    def test_no_instances_if_not_recurring(self):
        task = self._create_base_task()
        task.is_recurring = False
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, self.scheduling_end_date)
        self.assertEqual(len(instances), 0)

    def test_no_instances_if_no_original_start_date(self):
        task = self._create_base_task()
        task.recurrence_rule = "daily"
        task.original_start_date = None # Problem
        instances = self.scheduler._generate_recurrence_instances(task, self.scheduling_start_date, self.scheduling_end_date)
        self.assertEqual(len(instances), 0)
        
    def test_scheduling_window_filtering(self):
        task = self._create_base_task(original_start_str="2023-12-25") # Starts before window
        task.recurrence_rule = "daily"
        task.recurrence_interval = 1
        
        # Window: 2024-01-01 to 2024-01-03
        instances = self.scheduler._generate_recurrence_instances(task, dt.date(2024,1,1), dt.date(2024,1,3))
        self.assertEqual(len(instances), 3)
        self.assertEqual(instances[0].start_date, dt.date(2024,1,1))
        self.assertEqual(instances[-1].start_date, dt.date(2024,1,3))

        # Task ends before window
        task2 = self._create_base_task(original_start_str="2023-12-01")
        task2.recurrence_rule = "daily"
        task2.recurrence_end_date = dt.date(2023,12,5)
        instances2 = self.scheduler._generate_recurrence_instances(task2, dt.date(2024,1,1), dt.date(2024,1,3))
        self.assertEqual(len(instances2), 0)

    @patch('lurchcal.TaskScheduler.TaskScheduler._schedule_tasks_by_priority')
    def test_schedule_everything_expands_recurring_tasks(self, mock_schedule_by_priority):
        # Mock _schedule_tasks_by_priority to not actually schedule, just capture tasks
        mock_schedule_by_priority.return_value = ([], []) # Scheduled, Unscheduled

        recurring_daily = self._create_base_task("Daily Task", "2024-01-01")
        recurring_daily.recurrence_rule = "daily"
        recurring_daily.recurrence_count = 2 # Jan 1, Jan 2

        non_recurring = Task("Simple Task", start_date="2024-01-01")

        tasks_input = [recurring_daily, non_recurring]
        
        # schedule_everything sets up a 7-day window from start_date
        # For start_date 2024-01-01, this means act_start_date is 2024-01-01, end_date is 2024-01-08
        # Mock calendar and appointments are needed for schedule_everything
        mock_cal = Mock()
        
        self.scheduler.schedule_everything(mock_cal, dt.date(2024,1,1), tasks_input, [])
        
        self.assertTrue(mock_schedule_by_priority.called)
        args, _ = mock_schedule_by_priority.call_args
        expanded_tasks_received = args[0]
        
        self.assertEqual(len(expanded_tasks_received), 3) # 2 instances + 1 non-recurring
        
        # Check instance descriptions for the marker
        daily_task_instances = [t for t in expanded_tasks_received if t.description == "Daily Task [R]"]
        self.assertEqual(len(daily_task_instances), 2)

        non_recurring_found = any(t.description == "Simple Task" for t in expanded_tasks_received)
        self.assertTrue(non_recurring_found)

        for task in expanded_tasks_received:
            if task.description == "Daily Task [R]": # Check modified description
                self.assertFalse(task.is_recurring)
            elif task.description == "Simple Task": # Non-recurring task's description unchanged
                self.assertFalse(task.is_recurring) 
            # else: # This would catch unexpected tasks if any
                # self.fail(f"Unexpected task description: {task.description}")


if __name__ == "__main__":
    unittest.main() 