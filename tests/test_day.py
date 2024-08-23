# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

import unittest

# try:
#     import context
# except ModuleNotFoundError:
#     import tests.context
# import context

from datetime import datetime, time, date, timedelta

# import pyZimOutlookTasks.tests.context

from lurchcal.Day import Day, calc_overlap


class Task(object):
    def __init__(self, name):
        self.prio = 1
        self.descr = name
        self.duration = 0.1  # default duration is 6 minutes or .1 hours
        self.finish_date = None
        pass


class Test(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_Day(self):
        d = Day(date(2019, 1, 17))
        print(d.free_time_blocks)
        d.print()

        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 540)
        self.assertEqual(d.free_time(), 540)

        res = d.reserve_time(6)
        self.assertIsNotNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 6))
        self.assertEqual(d.free_time_blocks[0][1], 534)

        res = d.reserve_time(60)
        self.assertIsNotNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(10, 6))
        self.assertEqual(d.free_time_blocks[0][1], 474)

        res = d.reserve_time(473)
        self.assertIsNotNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(17, 59))
        self.assertEqual(d.free_time_blocks[0][1], 1)

        res = d.reserve_time(2)
        self.assertIsNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(17, 59))
        self.assertEqual(d.free_time_blocks[0][1], 1)

        res = d.reserve_time(1)
        self.assertIsNotNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(18, 0))
        self.assertEqual(d.free_time_blocks[0][1], 0)

        print(d.free_time_blocks)

    def test_block(self):
        d = Day(date(2019, 1, 17))

        d.block_time(time(10, 0), 50)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 60)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 50))
        self.assertEqual(d.free_time_blocks[1][1], 430)

        print(d.free_time_blocks)

        d = Day(date(2019, 1, 17))
        d.block_time(time(8, 0), 50)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 540)
        self.assertEqual(d.free_time(), 540)

        d = Day(date(2019, 1, 17))
        d.block_time(time(18, 0), 50)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 540)
        self.assertEqual(d.free_time(), 540)

        d = Day(date(2019, 1, 17))
        d.block_time(time(9, 0), 30)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 30))
        self.assertEqual(d.free_time_blocks[0][1], 510)

        d = Day(date(2019, 1, 17))
        d.block_time(time(8, 45), 30)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 15))
        self.assertEqual(d.free_time_blocks[0][1], 525)
        d.block_time(time(10, 0), 30)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 15))
        self.assertEqual(d.free_time_blocks[0][1], 45)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 30))
        self.assertEqual(d.free_time_blocks[1][1], 450)
        d.block_time(time(10, 15), 30)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 45))
        self.assertEqual(d.free_time_blocks[1][1], 435)
        d.block_time(time(12, 0), 90)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 45))
        self.assertEqual(d.free_time_blocks[1][1], 75)
        self.assertEqual(d.free_time_blocks[2][0].time(), time(13, 30))
        self.assertEqual(d.free_time_blocks[2][1], 270)
        d.block_time(time(16, 45), 90)
        self.assertEqual(d.free_time_blocks[2][0].time(), time(13, 30))
        self.assertEqual(d.free_time_blocks[2][1], 195)
        self.assertEqual(d.free_time(), 315)

        d.block_time(time(17, 45), 90)
        self.assertEqual(d.free_time_blocks[2][0].time(), time(13, 30))
        self.assertEqual(d.free_time_blocks[2][1], 195)
        self.assertEqual(d.free_time(), 315)
        # print(d.free_time_block, '\n')

    def test_Day_block_all(self):
        d = Day(date(2019, 1, 17))
        print(d.free_time_blocks)
        d.print()

        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 540)
        self.assertEqual(d.free_time(), 540)

        d.block_time(time(9, 0), 1440)
        self.assertEqual(len(d.free_time_blocks), 0)
        self.assertEqual(d.free_time(), 0)

    def test_block_overlap(self):
        d = Day(date(2019, 1, 17))

        d.block_time(time(10, 0), 50)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 60)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 50))
        self.assertEqual(d.free_time_blocks[1][1], 430)

        d.block_time(time(10, 15), 15)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 60)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(10, 50))
        self.assertEqual(d.free_time_blocks[1][1], 430)

        d.block_time(time(10, 45), 15)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(9, 0))
        self.assertEqual(d.free_time_blocks[0][1], 60)
        self.assertEqual(d.free_time_blocks[1][0].time(), time(11, 00))
        self.assertEqual(d.free_time_blocks[1][1], 420)

    def test_reserve(self):
        d = Day(date(2019, 1, 17))

        res = d.reserve_time(6)
        self.assertEqual(res[0].time(), time(9, 0))
        self.assertEqual(res[1], 6)

        res = d.reserve_time(6)
        self.assertEqual(res[0].time(), time(9, 6))
        self.assertEqual(res[1], 6)

        res = d.reserve_time(60)
        self.assertEqual(res[0].time(), time(9, 12))
        self.assertEqual(res[1], 60)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(10, 12))
        self.assertEqual(d.free_time_blocks[0][1], 468)

        res = d.reserve_time(600)
        self.assertIsNone(res)
        self.assertEqual(d.free_time_blocks[0][0].time(), time(10, 12))
        self.assertEqual(d.free_time_blocks[0][1], 468)

    def test_act_mon(self):
        o, ls, ee = calc_overlap(
            date(2021, 1, 1), date(2021, 1, 31), date(2021, 1, 15), date(2021, 2, 16)
        )
        pass
        # self.assertListEqual([1], months)

    def test1(self):
        tasks = [Task("a"), Task("b")]

        day = {}


#         schedule(tasks[0], day)

# self.assertEqual(day[datetime.time(9, 0)], tasks[0])


if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
