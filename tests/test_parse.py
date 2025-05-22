# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2025 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""
import unittest

from durations_nlp import Duration

from datetime import datetime, time, date, timedelta
from lurchcal.Task import Task

# https://pypi.org/project/durations-nlp/


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_parse(self):
        t = Task("Etwas checken !!! ~0.5h~ >2020-03-15 ")
        self.assertEqual(t.duration, 30)
        self.assertEqual(t.distribute_duration, True)
        self.assertEqual(t.assign_duration, False)

        t = Task("Etwas checken !!! ~0.5h~ >2020-03-15 #1h#")
        self.assertEqual(t.duration, 30)

        t = Task("Etwas checken !!! ~ 0.5h ~ >2020-03-15 #1h#")
        self.assertEqual(t.duration, 30)

        # Error in time
        t = Task("Etwas checken !!! ~0.5h >2020-03-15")
        self.assertEqual(t.duration, 6)

        # Error in time
        t = Task("Etwas checken !!! ~0.75  h # >2020-03-15")
        self.assertEqual(t.duration, 6)

    def test_param_a(self):
        t = Task("Etwas checken !!! ~0.5h~a >2020-03-15 ")
        self.assertEqual(t.duration, 30)
        self.assertEqual(t.distribute_duration, False)
        self.assertEqual(t.assign_duration, True)

        t = Task("Etwas checken !!! ~0.5h~ a >2020-03-15 ")
        self.assertEqual(t.duration, 30)
        self.assertEqual(t.distribute_duration, True)
        self.assertEqual(t.assign_duration, False)

    def test_Task(self):
        task = Task("Description  ~0.75h~ ", 1, "2023-12-31")
        self.assertEqual(task.start_date, date(2023, 12, 31))
        self.assertEqual(task.duration, 45.0)


class TestRecurrenceParsing(unittest.TestCase):
    def test_parse_daily_simple(self):
        task = Task("Daily meeting repeats: daily")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.description, "Daily meeting")

    def test_parse_daily_with_interval(self):
        task = Task("Check backups repeats: daily every 3 days")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 3)
        self.assertEqual(task.description, "Check backups")

    def test_parse_daily_with_end_date(self):
        task = Task("Morning sync repeats: daily until 2024-12-31")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_end_date, date(2024, 12, 31))
        self.assertEqual(task.description, "Morning sync")

    def test_parse_daily_with_count(self):
        task = Task("Log review repeats: daily count 5")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_count, 5)
        self.assertEqual(task.description, "Log review")

    def test_parse_weekly_simple(self):
        task = Task("Team lunch repeats: weekly")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "weekly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertIsNone(task.recurrence_on) # Defaults to start_date's day of week, not parsed here
        self.assertEqual(task.description, "Team lunch")

    def test_parse_weekly_with_interval_and_day(self):
        task = Task("Planning meeting repeats: weekly every 2 weeks on MON")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "weekly")
        self.assertEqual(task.recurrence_interval, 2)
        self.assertEqual(task.recurrence_on, "MON")
        self.assertEqual(task.description, "Planning meeting")

    def test_parse_weekly_with_end_date(self):
        task = Task("Sprint review repeats: weekly on FRI until 2025-03-01")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "weekly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_on, "FRI")
        self.assertEqual(task.recurrence_end_date, date(2025, 3, 1))
        self.assertEqual(task.description, "Sprint review")

    def test_parse_monthly_simple(self):
        task = Task("Pay bills repeats: monthly")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "monthly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertIsNone(task.recurrence_on) # Defaults to start_date's day of month, not parsed here
        self.assertEqual(task.description, "Pay bills")

    def test_parse_monthly_with_interval_and_day_number(self):
        task = Task("Report submission repeats: monthly every 3 months on 15")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "monthly")
        self.assertEqual(task.recurrence_interval, 3)
        self.assertEqual(task.recurrence_on, "15")
        self.assertEqual(task.description, "Report submission")

    def test_parse_monthly_with_last_weekday(self):
        task = Task("Book club repeats: monthly on last FRI")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "monthly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_on, "last FRI")
        self.assertEqual(task.description, "Book club")
        
    def test_parse_monthly_with_first_weekday(self):
        task = Task("Maintenance check repeats: monthly on first MON count 12")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "monthly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_on, "first MON")
        self.assertEqual(task.recurrence_count, 12)
        self.assertEqual(task.description, "Maintenance check")

    def test_parse_description_stripping(self):
        task = Task("Important task @urgent repeats: daily every 2 days until 2024-08-15 ~1h~a")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.description, "Important task @urgent ~1h~a") # Duration and tags remain part of desc for now
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 2)
        self.assertEqual(task.recurrence_end_date, date(2024, 8, 15))
        # Test that original duration/tag parsing is not broken
        self.assertEqual(task.duration, 60) # from ~1h~
        self.assertTrue(task.assign_duration) # from ~a
        self.assertIn("urgent", task.tags)

    def test_parse_description_stripping_tags_after_repeats(self):
        # This tests if tags are re-parsed correctly if they appear after the repeats clause, which they shouldn't normally.
        # However, the current implementation re-parses tags from the stripped description.
        task = Task("Task repeats: weekly @after")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.description, "Task @after") # @after should remain
        self.assertIn("after", task.tags)
        
    def test_parse_with_tags_and_duration_before_repeats(self):
        task = Task("Project X @work ~2h~ repeats: weekly on TUE count 3")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.description, "Project X @work ~2h~")
        self.assertEqual(task.recurrence_rule, "weekly")
        self.assertEqual(task.recurrence_interval, 1)
        self.assertEqual(task.recurrence_on, "TUE")
        self.assertEqual(task.recurrence_count, 3)
        self.assertEqual(task.duration, 120) # from ~2h~
        self.assertIn("work", task.tags)

    def test_parse_no_recurrence(self):
        task = Task("Simple task @home ~30m~")
        self.assertFalse(task.is_recurring)
        self.assertIsNone(task.recurrence_rule)
        self.assertEqual(task.description, "Simple task @home ~30m~")
        self.assertEqual(task.duration, 30)
        self.assertIn("home", task.tags)

    def test_parse_case_insensitivity(self):
        task = Task("Review docs REPEATS: DAILY EVERY 2 DAYS UNTIL 2025-01-01")
        self.assertTrue(task.is_recurring)
        self.assertEqual(task.recurrence_rule, "daily")
        self.assertEqual(task.recurrence_interval, 2)
        self.assertEqual(task.recurrence_end_date, date(2025, 1, 1))
        self.assertEqual(task.description, "Review docs")


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()


class TestDependencyParsing(unittest.TestCase):
    def test_parse_single_dependency(self):
        task = Task("Task B depends_on: 123")
        self.assertEqual(task.description, "Task B")
        self.assertEqual(task.depends_on_ids, [123])
        self.assertFalse(task.is_ready_to_schedule)

    def test_parse_multiple_dependencies(self):
        task = Task("Task C depends_on: 10,20,30")
        self.assertEqual(task.description, "Task C")
        self.assertEqual(task.depends_on_ids, [10, 20, 30])
        self.assertFalse(task.is_ready_to_schedule)

    def test_parse_dependencies_with_spaces(self):
        task = Task("Task D depends_on:  40 , 50 ")
        self.assertEqual(task.description, "Task D")
        self.assertEqual(task.depends_on_ids, [40, 50])
        self.assertFalse(task.is_ready_to_schedule)

    def test_parse_no_dependencies(self):
        task = Task("Task E")
        self.assertEqual(task.description, "Task E")
        self.assertEqual(task.depends_on_ids, [])
        self.assertTrue(task.is_ready_to_schedule)

    def test_parse_dependencies_empty_string_after_keyword(self):
        # New regex r"depends_on:\s*((?:[\d]+)(?:\s*,\s*[\d]+)*)" also won't match "depends_on: "
        # as it requires at least one digit for the dependency ID.
        # So dependency_match will be None, and description remains unchanged.
        original_description = "Task F depends_on: "
        task = Task(original_description)
        self.assertEqual(task.description, original_description) # Description unchanged
        self.assertEqual(task.depends_on_ids, [])
        self.assertTrue(task.is_ready_to_schedule)

    def test_parse_dependencies_empty_ids_among_valid(self):
        # Using pattern: r"depends_on:\s*((?:[\d]+)(?:\s*,\s*[\d]+)*)"
        # For "Task G depends_on: 1,,2", group(1) will be "1".
        # depends_on_ids will be [1].
        # group(0) will be "depends_on: 1".
        # Description will be "Task G ,,2" after stripping "depends_on: 1" and surrounding space.
        task = Task("Task G depends_on: 1,,2")
        self.assertEqual(task.description, "Task G ,,2")
        self.assertEqual(task.depends_on_ids, [1])
        self.assertFalse(task.is_ready_to_schedule)

    def test_parse_dependencies_with_tags_and_duration(self):
        task = Task("Task H @work ~2h~ depends_on: 70,80")
        self.assertEqual(task.description, "Task H @work ~2h~")
        self.assertEqual(task.depends_on_ids, [70, 80])
        self.assertFalse(task.is_ready_to_schedule)
        self.assertIn("work", task.tags)
        self.assertEqual(task.duration, 120)

    def test_parse_dependencies_case_insensitivity(self):
        task = Task("Task I DEPENDS_ON: 90")
        self.assertEqual(task.description, "Task I")
        self.assertEqual(task.depends_on_ids, [90])
        self.assertFalse(task.is_ready_to_schedule)

    def test_parse_dependencies_invalid_id_skipped(self):
        # The regex ([\d,]+) ensures only digits and commas are in ids_str.
        # If an invalid part like 'abc' was somehow included (e.g. if regex was looser),
        # the int(id_str.strip()) would raise ValueError, and that ID would be skipped.
        # Current regex: r"depends_on:\s*([\d,]+)"
        # For "Task J depends_on: 123,abc,456", group(1) would be "123,"
        # So only 123 would be parsed. This is fine.
        task = Task("Task J depends_on: 123,abc,456")
        self.assertEqual(task.description, "Task J depends_on: 123,abc,456".replace("depends_on: 123","").strip()) # depends_on: 123 is removed
        self.assertEqual(task.depends_on_ids, [123]) 
        self.assertFalse(task.is_ready_to_schedule)

        task_only_invalid = Task("Task K depends_on: abc,def")
        # dependency_match would be None because \d won't match abc or def
        self.assertEqual(task_only_invalid.description, "Task K depends_on: abc,def")
        self.assertEqual(task_only_invalid.depends_on_ids, [])
        self.assertTrue(task_only_invalid.is_ready_to_schedule)

    def test_is_ready_to_schedule_logic(self):
        task_with_deps = Task("Task L depends_on: 1")
        self.assertFalse(task_with_deps.is_ready_to_schedule)
        
        task_without_deps = Task("Task M")
        self.assertTrue(task_without_deps.is_ready_to_schedule)

        # Test that is_ready_to_schedule becomes true if depends_on_ids is initially set then cleared (e.g. invalid parse)
        # This case is covered by test_parse_dependencies_empty_string_after_keyword or test_parse_dependencies_invalid_id_skipped
        task_initially_true = Task("Task N")
        task_initially_true.depends_on_ids = [1] # Manually set for test
        task_initially_true.is_ready_to_schedule = False # Manually set for test
        
        # Simulate parsing an empty or invalid dependency string for this task
        # This requires re-evaluating the logic within the parse method or a separate method
        # For this test, we'll check the state after parsing specific strings
        task_parsed_empty_deps = Task("Task O depends_on: ")
        self.assertTrue(task_parsed_empty_deps.is_ready_to_schedule)

    def test_description_stripping_and_tag_reparsing(self):
        task = Task("Task P @initial depends_on: 100 @final")
        self.assertEqual(task.description, "Task P @initial @final")
        self.assertEqual(task.depends_on_ids, [100])
        self.assertFalse(task.is_ready_to_schedule)
        self.assertIn("initial", task.tags)
        self.assertIn("final", task.tags) # Check if tags after dependency are kept and reparsed

        task2 = Task("Task Q depends_on: 200 @final")
        self.assertEqual(task2.description, "Task Q @final")
        self.assertEqual(task2.depends_on_ids, [200])
        self.assertIn("final", task2.tags)
        
        task3 = Task("@start Task R depends_on: 300")
        self.assertEqual(task3.description, "@start Task R")
        self.assertEqual(task3.depends_on_ids, [300])
        self.assertIn("start", task3.tags)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
