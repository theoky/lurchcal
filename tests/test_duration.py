# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

import unittest

from durations_nlp import Duration

# https://pypi.org/project/durations-nlp/


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_extract_duration(self):

        self.assertEqual(Duration("2 days, 3h").to_minutes(), 3060)
        self.assertEqual(Duration("5m").to_minutes(), 5)
        self.assertEqual(Duration(" 5 m ").to_minutes(), 5)
        self.assertEqual(Duration(" 0.25h ").to_minutes(), 15)
        self.assertEqual(Duration(" 0.25h ").to_minutes(), 15)
        self.assertEqual(Duration(" 0.25h ").to_minutes(), 15)
        self.assertEqual(Duration(" 0.75h ").to_minutes(), 45)
        self.assertEqual(Duration(" 1 h ").to_minutes(), 60)
        self.assertEqual(Duration(" #1 h# ".split("#")[1]).to_minutes(), 60)


#        self.assertEqual(Duration(" This will take 5 m ").to_minutes(), 5)


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
