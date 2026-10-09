# LurchCal Documentation

## Introduction

## Browser workflow (AP5)

Start the separate Task Server (`python -m task_server`) and then LurchCal Web Server (`python -m lurchcal.web_server`) with the project's Python environment active and `src` on `PYTHONPATH`. Open `http://127.0.0.1:8000`. The Schedule page has a **Calendar & scheduling** tab, selected by default, with a day-view calendar and the create/publish, create-and-add-calendar-appointments, and remove-LurchCal-appointments actions. The **Task lists** tab contains the open task list and latest scheduled/unscheduled results. Long operations run as background jobs; the page polls job progress and displays results. Use Settings to enter the LurchCal Task Server URL, choose Outlook or Google Calendar, set the scheduling horizon, and enter the Task Server's Zim database and schedule-page paths. Save validates typed LurchCal settings and tests provider/service availability. Source paths are text inputs because they are paths on the Task Server's machine; the browser never selects or reads those files. Validate the Task Server/Zim source before scheduling. The calendar supports month, week and day views, requests data only for the visible range, and is view-only. Frontend assets are pinned and served locally.

## Adding information to tasks

Task in ZIM already have meta information:

- start or due date, e.e. <2024-12-23 means due before Christmas.
- priority, designated with '!'. Multiple questionmarks denote higher priority [^1].
- Tasks can contain tags, starting with '@'.
  
This tool adds the following additional meta data:
- '\~' duration '\~' ['a']

This specifies the duration of a task, whereas duration can be written in hours, minutes, etc. If no duration is specfied, a configurable value is assigned (e.g., 6 min).

If the duration is specified at the top level task of subtasks, the duration is distributed evenly among the subtasks.
If 'a', which is optional, is specified, each subtasks gets assigned the specified duration of the parent task.

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
