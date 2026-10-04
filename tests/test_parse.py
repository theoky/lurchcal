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

    def test_default_duration_tags_and_dates(self):
        task = Task("Review notes @Deep @TEAM", start_date="2024-01-02", due_date="2024-02-03")
        self.assertEqual(task.duration, 6)
        self.assertEqual(task.tags, ["deep", "team"])
        self.assertEqual(task.start_date, date(2024, 1, 2))
        self.assertEqual(task.due_date, date(2024, 2, 3))


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
