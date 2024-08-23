# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
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

        t = Task("Etwas checken !!! ~0.5h~ >2020-03-15 #1h#")
        self.assertEqual(t.duration, 30)

        # Error in time
        t = Task("Etwas checken !!! ~0.5h >2020-03-15")
        self.assertEqual(t.duration, 6)

        # Error in time
        t = Task("Etwas checken !!! ~0.75  h # >2020-03-15")
        self.assertEqual(t.duration, 6)

    def test_Task(self):
        task = Task("Description  ~0.75h~ ", 1, "2023-12-31")
        self.assertEqual(task.start_date, date(2023, 12, 31))
        self.assertEqual(task.duration, 45.0)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
