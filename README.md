# LurchCal

## Introduction

LurchCal[^1] is a tool which should help to improve personal efficiency[^2].

As a long time user of [ZIM](https://github.com/zim-desktop-wiki) for taking  notes and managing tasks, there was always one challenge: As there are also a significant amount of meetings, keeping some non-meeting time available for working on the tasks can be challenging.

One way to handle that is to create appointments in the calendar just for tasks[^3]. Doing that manually is not feasible, so automation is needed.

This is where this tool comes into play. The workflow with this tool is as follows:

- user
  - enriches tasks in ZIM with meta information like duration, e.g. a task with the text "do something 30m" will take 30min (probably).
- tool
  - build an internal scheduling calendar with my available working time
  - get all appointments from my calendar and remove them from the available working time, thus creating a digital twin calendar.
  - add some default appointments (e.g. lunch break) - or not.
    - now the internal calendar contains only time left which is available for working on tasks.
  - schedule all tasks with a given duration as appointments. Tasks with no duration specified will take a default amount of time (e.g. 6min). Tasks longer than an hour will be split into subtasks of max. one hour length.
  - schedule according to priority and tags (e.g. ILM (Ivy Lee Method) tasks should be handled first, because they should be done today, then legal task, and so on)
  - see what can't get scheduled and drops out.

The resulting schedule can then be presented as a ZIM page or additionally as appointments in Outlook, so that they block time for work instead for meetings.
As a bonus, it works without cloud.

## Status

This tool is currently in prealpha and a work in progress. It lacks tests and documentation.

## How to use it

    #TBD

## Requirements

- ZIM for the tasks
- a calendar, currently only Outlook is supported
- Python 3.11
- this tool

## Setup

- install Python 3.11.7, e.g. in a conda environment
- install requirements
- start LurchCalApp.py

## Technical Info

- Communication with Outlook is done via MAPI.

[^1]: The name Lurch is inspired by the grumpy buttler from the Addams Familiy. This tool is sometimes also grumpy.

[^2]: One can frown upon this endeavour, I know.

[^3]: This idea I've first seen somewhen around 2006.
