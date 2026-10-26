# LurchCal

## Introduction

LurchCal[^1] is a tool which aims to improve personal efficiency[^2].

As a long time user of [ZIM](https://github.com/zim-desktop-wiki) for taking notes and managing tasks, there always has been one challenge: As there are also a significant amount of meetings, keeping some non-meeting time available for working on the tasks can be challenging and blocking focus time, e.g. in Outlook, doesn't help always.

One way to handle that is to create appointments in the calendar just for tasks[^3]. That way you can plan your work and get an idea if there are too many appointments removing time budget from your takss. Doing that manually is not feasible, so automation is needed.

This is where this tool comes into play. The workflow with this tool is as follows:

- user
  - enriches tasks in ZIM with meta information like duration, e.g. a task with the text "do something 30m" will take 30min (probably). It is not [org mode for EMACS](https://orgmode.org/).
- tool
  - builds an internal scheduling calendar with my available working time
  - gets all appointments from my calendar and removes them from the available working time, thus creating a digital twin of my calendar.
  - adds some default appointments (e.g. lunch break) (or not, depends on you, resp. the configuration).
    - now the internal calendar contains only time left which is available for working on tasks.
  - schedules all tasks with a given duration as appointments. Tasks with no duration specified will take a default amount of time (e.g. 6min). Tasks longer than an hour will be split into subtasks of max. one hour length.
  - schedules according to priority and tags (e.g. ILM (Ivy Lee Method) tasks should be handled first, because they should be done today, then legal task, and so on)
  - see what can't get scheduled and drops out.

The resulting schedule can then be presented as a ZIM page or additionally as appointments in Outlook, so that they block time for work instead for meetings.

As a bonus, it works without cloud.

## Status

This tool is currently in alpha and work in progress. It lacks some tests, good documentation, and probably much more. The startup process is currently a little bit manual.

## How to use it

See [documentation.md](documentation.md) in this directory.

## Requirements

- ZIM for the tasks
- a calendar, Outlook is supported, Google Calendar is on its way.
- Python 3.11
- this tool

## Starting the application

For Task Server setup, API configuration, and browser application startup instructions, see [Starting LurchCal](documentation.md#starting-lurchcal) in `documentation.md`.

## Testing

The test suite uses pytest with per-test SQLite databases generated from deterministic fixtures to avoid file-locking issues on Windows. Fixtures in `tests/conftest.py` provide `db_path`, `db_conn`, `ro_conn`, and `engine`, building a fresh database via `tests/zim_test_utils.initialize_zim_sqlite` for every test or worker. Because the schema is synthesized on demand, no binary SQLite file is stored in the repository. Connections and SQLAlchemy engines are closed and disposed during teardown, which is essential on Windows for releasing handles before temporary files are removed.

On Windows, activate the project Python environment before testing with `C:\apps\ac3\Scripts\activate && conda activate lurchcal`. Then run the suite with `python -m pytest -q`, or in parallel with `python -m pytest -q -n auto` (requires `pytest-xdist`). When adding database-dependent tests, depend on the fixtures instead of opening the fixture file directly.

## Technical Info

- Communication with Outlook is done via MAPI.

# End Notes
[^1]: The name Lurch is inspired by the grumpy buttler from the Addams Familiy. This tool (and its author) is sometimes also grumpy.

[^2]: One can frown upon this endeavour, I know.

[^3]: This idea I've first seen somewhen around 2006.
