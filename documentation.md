# LurchCal Documentation

## Introduction

## Starting LurchCal

### Configure and start the Task Server

The independent Task Server runs as a separate process on `127.0.0.1:8001` by default. Install the project requirements and start it from the repository root:

```text
python -m task_server
```

For a source checkout, ensure `src` is on `PYTHONPATH` (for example, run `set PYTHONPATH=src` in Windows Command Prompt). The server stores its local source settings in `%LOCALAPPDATA%\LurchCal\task_server.ini`; set `LURCHCAL_TASK_SERVER_CONFIG` to use another INI location. Configure the Zim database and schedule-page paths through `PUT /api/v1/settings`, then check them with `POST /api/v1/settings/validate`.

Useful API requests include `GET /api/v1/health`, `GET /api/v1/capabilities`, and `GET /api/v1/tasks?as_of=2026-10-04`. Settings use `{"path_db":"C:\\...\\index.db","path_page":"C:\\...\\Geplante_Tasks.txt"}`. A schedule-publication request uses `{"scheduled_tasks":[{"start":"2026-10-05T09:00:00","duration":30,"priority":2,"description":"Write report","tags":["work"],"source_name":"Work"}]}`.

The versioned API provides health, capabilities, read-only task retrieval, settings, validation, and schedule publication endpoints. It does not expose task mutation operations. Configure the Task Server base URL in LurchCal if it differs from `http://127.0.0.1:8001`; configure Zim database and schedule-page paths on the Task Server. Removing calendar appointments remains a calendar-only action.

### Start and use the browser app

With the project's Python environment active and `src` on `PYTHONPATH`, start the LurchCal Web Server after the Task Server:

```text
python -m lurchcal.web_server
```

Open `http://127.0.0.1:8000`. The Schedule page has a **Calendar & scheduling** tab, selected by default, with a day-view calendar and the create/publish, create-and-add-calendar-appointments, and remove-LurchCal-appointments actions. The **Task lists** tab contains the open task list and latest scheduled/unscheduled results. Long operations run as background jobs; the page polls job progress and displays results. Use Settings to enter the LurchCal Task Server URL, choose Outlook or Google Calendar, set the scheduling horizon, and enter the Task Server's Zim database and schedule-page paths. Saving validates typed LurchCal settings and tests provider/service availability. Source paths are entered as text because they are paths on the Task Server's machine; the browser never selects or reads those files. Validate the Task Server/Zim source before scheduling. The calendar supports month, week and day views, requests data only for the visible range, and is view-only. Frontend assets are pinned and served locally.

## Adding information to tasks

Task in ZIM already have meta information:

- start or due date, e.e. \<2024-12-23 means due before Christmas.
- priority, designated with '!'. Multiple questionmarks denote higher priority [^1].
- Tasks can contain tags, starting with '\@'.

This tool adds the following additional meta data: - '\~' duration '\~' \['a'\]

This specifies the duration of a task, whereas duration can be written in hours, minutes, etc. If no duration is specfied, a configurable value is assigned (e.g., 6 min).

If the duration is specified at the top level task of subtasks, the duration is distributed evenly among the subtasks. If 'a', which is optional, is specified, each subtasks gets assigned the specified duration of the parent task.

## Scheduling of tasks

Tasks are per default scheduled as follows:

- tasks with ILM tag - ILM stands for Ivy Lee Method
- tasks with prio \>= 3 and a due date
- tasks with prio \>=3
- repeat for tasks with prio 2, 1 and none

### Examples

> - [ ] task which lasts 10 minutes \~10m\~
> - [ ] task with each subtasks lasting 5 minutes \~10m\~
>   - [ ] task lasts 5 min (automatically computed)
>   - [ ] task also lasts 5 min (automatically computed)
> - [ ] task with each subtasks lasting 15 minutes \~15m\~a
>   - [ ] task lasts 15 min (assigned from parent)
>   - [ ] task also lasts 15 min (assigned from parent)

# End Notes

[^1]: Although Terry Pratchett argued that "Multiple exclamation marks are a sure sign of a diseased mind." Maybe he was a project manager?
