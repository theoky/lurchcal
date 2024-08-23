# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# Copyright (C) 2023-2024 theoky
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
"""
"""

from datetime import datetime, time, date, timedelta
from collections import namedtuple

# @class method
# def func(cls, args...)


def calc_overlap(i1b, i1e, i2b, i2e):
    Range = namedtuple("Range", ["start", "end"])

    r1 = Range(start=i1b, end=i1e)
    r2 = Range(start=i2b, end=i2e)

    latest_start = max(r1.start, r2.start)
    earliest_end = min(r1.end, r2.end)

    if earliest_end < latest_start:
        delta = -(latest_start - earliest_end).seconds / 60
    else:
        delta = (earliest_end - latest_start).seconds / 60

    overlap = max(0, delta)
    return (overlap, latest_start, earliest_end)


class Day(object):
    def __init__(self, day: date, start_of_day=time(9, 0), hours=9):
        self.date = day
        self.free_time_blocks = [
            [datetime.combine(self.date, start_of_day), hours * 60]
        ]

    def create_block(self, b, minutes):
        """Create a bookable timeblock for the day of self

        Args:
            b (_type_): datetime, time is relevant
            minutes (_type_): length of block

        Returns:
            _type_: _description_
        """
        if minutes > 0:
            return [datetime.combine(self.date, b.time()), minutes]
        return None

    def block_time(self, time, minutes):
        # find block which contains the block to take out
        # split it

        res_list = []
        for idx in range(len(self.free_time_blocks)):

            bdt = self.free_time_blocks[idx][0]
            bmin = self.free_time_blocks[idx][1]

            o, s, e = calc_overlap(
                bdt,
                bdt + timedelta(minutes=bmin),
                datetime.combine(bdt, time),
                datetime.combine(bdt, time) + timedelta(minutes=minutes),
            )

            if o > 0:
                b1 = self.create_block(bdt, (s - bdt).seconds / 60)
                b2 = self.create_block(e, bmin - (e - bdt).seconds / 60)

                res_list += [b1] if b1 is not None else []
                res_list += [b2] if b2 is not None else []
            else:
                res_list.append(self.free_time_blocks[idx])

        self.free_time_blocks = res_list

    def reserve_time(self, minutes):
        if self.free_time() < minutes:
            return None

        # first fit algorithm
        for idx in range(len(self.free_time_blocks)):

            bdt = self.free_time_blocks[idx][0]
            bmin = self.free_time_blocks[idx][1]

            if bmin >= minutes:
                self.free_time_blocks[idx][0] = bdt + timedelta(minutes=minutes)
                self.free_time_blocks[idx][1] -= minutes

                nb = self.create_block(bdt, minutes)
                return nb

        return None

    def free_time(self):
        """Return the free time in minutes of the day

        Returns:
            int: free time in mimutes
        """
        return sum([b[1] for b in self.free_time_blocks])

    def print(self):
        print("Time blocks of day " + str(self.date))
        for idx in range(len(self.free_time_blocks)):

            bdt = self.free_time_blocks[idx][0]
            bmin = self.free_time_blocks[idx][1]

            print(bdt, bmin)
