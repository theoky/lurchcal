# LurchCal Target Architecture

## 1. Purpose

This document defines the target architecture for the migration of LurchCal from a Kivy desktop UI with direct Zim access to a local browser application with an independent task service.

It is an architectural contract for humans and coding agents. During the migration, implementation details may evolve, but the invariants in section 4 must not be violated without explicitly changing this document first.

## 2. Confirmed decisions

The following decisions are fixed for the current migration:

1. The **Task Server is a separate local process**.
2. LurchCal remains a **single-user local application** for now.
3. The existing **Zim schedule page is retained**.
4. Tasks exposed by the Task Server are **read-only**. There is no task create/update/delete API in this migration.
5. Schedule publication is a separate output capability and is not considered task CRUD.
6. The browser UI will use **FastAPI + Jinja2 + HTMX + Alpine.js** rather than Svelte/SvelteKit for this migration.
7. A calendar view is implemented with **FullCalendar (vanilla JavaScript)**, using LurchCal HTTP endpoints for event data.
8. Both Python services bind to **127.0.0.1 by default**. Authentication and TLS are out of scope while the application remains local-only.
9. The migration is incremental: first decouple Zim, then introduce the browser UI, and only then remove Kivy.

## 3. Current architecture

The current repository is centered around `src/LurchCalApp.py` and `src/lurchcal/lurchcal_wf.py`.

```text
Kivy UI (src/LurchCalApp.py)
        |
        v
lurchcal_wf.py
   |---- TaskParser ----------------------> Zim SQLite index.db
   |---- TaskScheduler / Day / Task
   |---- CalendarFactory -----------------> Outlook COM / Google Calendar
   `---- write_to_zim_page() -------------> Zim wiki page file
```

Important current couplings:

- `TaskParser.py` imports `sqlite3` and reads Zim's `tasklist` and `pages` tables directly.
- `lurchcal_wf.py` reads `zim.path_db`, writes `zim.path_page`, creates the calendar adapter, orchestrates scheduling, and reports progress through a GUI callback.
- `TaskScheduler.py`, `TaskParser.py`, `task_tools.py`, `CalendarOutlook.py`, `CalendarGoogle.py`, and `lurchcal_wf.py` depend on `kivy.logger` and/or Kivy configuration.
- `LurchCalApp.py` owns both UI and configuration parsing.
- Outlook uses `win32com.client`; it must continue to execute in local Python and must not move into browser JavaScript.
- The existing UI starts work in background threads. Any new background-job implementation must respect Outlook COM thread affinity.

## 4. Architectural invariants

These rules are mandatory throughout and after the migration.

### 4.1 Zim isolation

Only the Task Server's Zim adapter may know about:

- Zim SQLite schema (`tasklist`, `pages`);
- the path to Zim's `index.db`;
- the Zim wiki page file format;
- the configured schedule-page path;
- other Zim-specific filesystem details.

The LurchCal scheduling core, LurchCal web UI, and calendar adapters must not access Zim directly.

### 4.2 Task Server boundary

The Task Server exposes a source-neutral, versioned HTTP interface. Its first implementation is `ZimTaskSource`, but callers must not depend on Zim-specific fields.

Tasks are read-only. The API must not add task mutation endpoints during this migration.

Publishing the generated schedule is a separate capability, for example:

```text
POST /api/v1/schedule-publications
```

This writes a schedule representation through the configured task source but does not mutate task records.

### 4.3 Scheduling-domain independence

Scheduling-domain code must not depend on:

- Kivy;
- FastAPI;
- Jinja2;
- HTMX;
- Alpine.js;
- FullCalendar;
- HTTP client details;
- Zim SQLite details.

`TaskScheduler`, `Day`, `Task`, `ScheduledTask`, and task-interpretation rules remain ordinary Python domain/application code.

### 4.4 Browser boundary

The browser communicates only with the **LurchCal Web Server**.

```text
Browser -> LurchCal Web Server -> Task Server
```

The browser must not call the Task Server directly. This keeps task-source substitution invisible to the UI and avoids multiple browser-side service configurations.

### 4.5 Local-first deployment

Default topology:

```text
127.0.0.1:8000  LurchCal Web Server
127.0.0.1:8001  Task Server
```

Ports are configurable. Do not bind to `0.0.0.0` by default.

### 4.6 Calendar isolation

Calendar providers remain behind the existing calendar abstraction/factory. Platform-specific imports must remain confined to adapters.

For Outlook, COM objects must be created and used on the same worker thread. Do not share Outlook COM objects across threads. If the worker implementation requires explicit COM initialization, use `pythoncom.CoInitialize()` / `CoUninitialize()` inside that worker boundary.

## 5. Target architecture

```text
+-------------------------------------------------------------+
| Browser                                                     |
|                                                             |
|  Jinja2-rendered pages                                      |
|  HTMX          -> server actions / fragments / polling      |
|  Alpine.js     -> small local UI state                      |
|  FullCalendar  -> calendar rendering                        |
+-------------------------------+-----------------------------+
                                |
                                | HTTP (HTML + JSON)
                                v
+-------------------------------------------------------------+
| LurchCal Web Server (FastAPI, local process)                |
|                                                             |
|  Web routes / templates / static assets                     |
|  Job service                                                |
|  Settings facade                                            |
|  Calendar event API for FullCalendar                        |
|                |                                            |
|                v                                            |
|  SchedulingService / application layer                      |
|     |                         |                              |
|     v                         v                              |
|  TaskServerClient       CalendarFactory                     |
|                          |          |                        |
|                          v          v                        |
|                       Outlook     Google                     |
+------------+------------------------------------------------+
             |
             | versioned REST/JSON
             v
+-------------------------------------------------------------+
| Task Server (FastAPI, separate local process)               |
|                                                             |
|  /api/v1/health                                             |
|  /api/v1/capabilities                                       |
|  /api/v1/tasks                                              |
|  /api/v1/settings                                           |
|  /api/v1/schedule-publications                              |
|                |                                            |
|                v                                            |
|  TaskSource abstraction                                     |
|                |                                            |
|                v                                            |
|  ZimTaskSource                                              |
|     |                        |                               |
|     v                        v                               |
|  SQLite index.db       Zim schedule page                    |
+-------------------------------------------------------------+
```

## 6. Task Server contract

### 6.1 Task model

The HTTP task representation must contain only task-source-neutral concepts needed by LurchCal. A suitable initial model is:

```text
id: string
parent_id: string | null
description: string
priority: integer
start_date: YYYY-MM-DD | null
due_date: YYYY-MM-DD | null
source_name: string | null
has_children: boolean
```

Additional generic fields may be added only when they have a demonstrated LurchCal use case. Do not expose SQLite column names merely because they exist.

The current LurchCal semantics for `~duration~`, `~duration~a`, `@tags`, duration inheritance, and task splitting remain **LurchCal interpretation rules**, not Zim adapter rules.

### 6.2 Task query semantics

The existing implementation selects open, non-waiting tasks whose start date is not in the future. Preserve this effective behavior but make the reference date explicit so tests are deterministic.

Recommended endpoint:

```text
GET /api/v1/tasks?as_of=2026-10-04
```

The Task Server maps this generic query to the source-specific Zim SQL. Do not use SQLite `date()` as the only source of time inside tests.

### 6.3 Health and capabilities

Minimum endpoints:

```text
GET /api/v1/health
GET /api/v1/capabilities
GET /api/v1/tasks?as_of=YYYY-MM-DD
```

A representative capabilities response may state:

```json
{
  "task_read": true,
  "task_write": false,
  "schedule_publish": true,
  "settings_write": true
}
```

### 6.4 Schedule publication

The existing `write_to_zim_page()` behavior must move behind the Task Server boundary.

Suggested endpoint:

```text
POST /api/v1/schedule-publications
```

The payload should be a source-neutral schedule DTO containing scheduled entries and enough source information to reproduce the current Zim page. Rendering Zim wiki syntax belongs to `ZimTaskSource` or a Zim-specific publisher component.

### 6.5 Task Server settings

The Task Server owns source-specific configuration. Initial Zim settings include at least:

- `path_db` – required for task reading;
- `path_page` – required if schedule publication is enabled.

The current repository also contains `path_exe` and `path_wiki`, but the current workflow does not use them. Treat them as legacy/optional unless implementation work demonstrates a real need.

The LurchCal browser settings page may manage Task Server settings, but the browser must do so through the LurchCal Web Server, which proxies/delegates to the Task Server.

## 7. LurchCal application layer

Introduce a UI-independent application service, conceptually:

```text
SchedulingService.create_schedule(...)
SchedulingService.remove_calendar_appointments(...)
```

The scheduling workflow is:

```text
TaskServerClient.get_tasks(as_of)
        |
        v
interpret TaskRecord -> LurchCal Task
        |
        v
build hierarchy / inherited metadata / split tasks
        |
        v
CalendarFactory -> fetch existing appointments
        |
        v
TaskScheduler
        |
        +--> optional calendar appointment creation
        |
        `--> TaskServerClient.publish_schedule(...)
```

The application service returns structured results rather than driving a GUI callback directly.

A useful result model contains:

```text
scheduled_tasks
unscheduled_tasks
warnings
statistics
```

Progress reporting should use application-level progress events/callbacks that are not tied to Kivy widgets.

## 8. Configuration architecture

During migration, retain INI-based persistence unless there is a concrete reason to change it. Avoid combining a UI migration with an unnecessary configuration-format migration.

### LurchCal-owned settings

Examples:

- appointment/scheduling horizon;
- working day start and length;
- breaks;
- task default/split duration;
- tag ordering and semantics;
- calendar provider;
- Task Server base URL.

### Task Server-owned settings

Examples:

- Zim database path;
- Zim schedule-page path;
- optional future task-source settings.

Typed configuration objects should be introduced between persistence and domain logic. Domain code must not receive Kivy `ConfigParser` instances.

## 9. Web UI architecture

### 9.1 Technology roles

Use each technology for a narrow purpose:

- **Jinja2**: page structure and server-rendered HTML;
- **HTMX**: actions, partial refreshes, forms, polling, error/result fragments;
- **Alpine.js**: small local UI state such as dialogs, tabs, visibility, and dependent controls;
- **FullCalendar (vanilla JS)**: calendar visualization.

Do not build a SPA state-management layer in Alpine.js.

### 9.2 Main page

The browser UI must initially reach parity with the Kivy UI:

- create schedule / publish schedule page;
- create schedule and calendar appointments;
- remove LurchCal-generated calendar appointments;
- show progress/job status;
- show unscheduled tasks;
- expose configuration.

It should additionally show scheduled tasks because the web UI can do so cheaply and this supports the calendar view.

### 9.3 Calendar view

FullCalendar receives normalized events from the LurchCal server, for example:

```text
GET /api/v1/calendar/events?start=...&end=...
```

The endpoint can combine, where useful:

- existing calendar appointments;
- generated/planned LurchCal task slots.

Do not expose Outlook/Google provider objects or provider-specific payloads directly to the browser.

The first version is a view/inspection surface. Drag/drop editing and rescheduling are out of scope unless explicitly added later.

## 10. Background jobs

Scheduling and calendar modification must not block a web request until completion.

For the current single-user app, use a deliberately small local job mechanism rather than Celery/Redis:

```text
queued -> running -> succeeded | failed
```

An in-memory job registry plus a controlled worker/executor is sufficient initially.

HTMX can poll a job-status fragment or JSON endpoint. Preserve meaningful progress stages from the current callback-driven workflow without coupling them to six hard-coded GUI increments.

## 11. Migration strategy

Use a strangler-style migration:

```text
Stage A
Kivy -> LurchCal core -> Zim

Stage B
Kivy -> LurchCal core -> Task Server -> Zim

Stage C
Browser -> LurchCal web/core -> Task Server -> Zim

Stage D
Kivy removed
```

Do not change the task-source boundary and user interface in the same work package.

## 12. Explicit non-goals

The following are not part of this migration:

- task editing or CRUD through the Task Server;
- multi-user operation;
- cloud deployment;
- user accounts/authentication;
- public network exposure;
- Redis/Celery;
- a new scheduling algorithm;
- drag/drop calendar editing;
- replacing Outlook/Google calendar adapters;
- adding additional task providers.

The architecture should allow later evolution, but agents must not implement these features opportunistically.

## 13. Current repository facts that agents must preserve or account for

- Python 3.11 is the documented project runtime.
- Tests already include deterministic per-test Zim SQLite fixtures in `tests/zim_test_utils.py` and `tests/conftest.py`.
- The fixture strategy was introduced specifically to avoid SQLite file-locking problems on Windows. Reuse it instead of adding a shared mutable fixture database.
- `Task.parse()` currently implements duration and `@tag` parsing; `TaskParser` has overlapping parsing logic. Refactoring may consolidate duplication, but semantics must be protected by tests first.
- `TaskParser._read_zim_tasks()` currently filters `status = 0`, `not waiting`, and `start <= date()` and orders by due date, priority, and start date.
- `write_to_zim_page()` in `lurchcal_wf.py` defines the current schedule-page output format.
- `CalendarOutlook` uses `win32com.client` and `CalendarGoogle` uses Google's API libraries.
- Kivy must remain operational through the end of work package AP3; it is removed only in AP6.
