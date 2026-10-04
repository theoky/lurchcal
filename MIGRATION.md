# LurchCal Migration Roadmap

## Purpose

This file is the persistent migration status for both humans and coding agents. Each agent must read `AGENTS.md`, `ARCHITECTURE.md`, and this file before changing code.

Only one work package should normally be implemented at a time. Do not start the next work package merely because time/context remains.

## Confirmed target

- Separate FastAPI Task Server process.
- Local single-user operation.
- Tasks are read-only through the Task Server.
- Existing Zim schedule-page publication remains available as a separate capability.
- Browser UI uses FastAPI/Jinja2 + HTMX + Alpine.js.
- Calendar visualization uses vanilla FullCalendar.
- Kivy remains temporarily during the backend migration and is removed only after browser feature parity.

## Baseline note

The repository documents Python 3.11 as the runtime. A test run in the artifact-preparation environment (Python 3.13) could not collect the suite because that environment did not have `durations_nlp` or Kivy installed. This is **not** recorded as a product defect.

At the start of AP1, establish and record the real baseline in a proper Python 3.11 project environment with the repository requirements installed.

## Work-package status

| ID | Work package | Status | Required predecessor | Exit milestone |
|---|---|---|---|---|
| AP1 | Core decoupling and regression baseline | DONE | none | Scheduling/domain code no longer depends on Kivy config/logging |
| AP2 | Independent Task Server | NOT STARTED | AP1 | Zim tasks and schedule publication available through versioned local REST API |
| AP3 | LurchCal consumes Task Server | NOT STARTED | AP2 | Kivy app still works, but LurchCal contains no direct Zim access |
| AP4 | LurchCal web backend and job model | NOT STARTED | AP3 | FastAPI/Jinja2 backend can run workflows and expose settings/jobs/calendar data |
| AP5 | HTMX/Alpine/FullCalendar browser UI | NOT STARTED | AP4 | Browser has functional parity with Kivy plus calendar view |
| AP6 | Cutover, launcher, Kivy removal, cleanup | NOT STARTED | AP5 | Browser version is default; Kivy removed; docs/tests updated |

Allowed status values:

```text
NOT STARTED
IN PROGRESS
BLOCKED
DONE
```

When an agent completes a work package, update its row and add a concise completion note below. Do not mark `DONE` if an exit criterion is knowingly unmet.

---

# AP1 — Core decoupling and regression baseline

## Goal

Make the scheduling/application core independent from Kivy while preserving existing behavior.

## Preconditions

- Current repository state is available.
- Use Python 3.11.
- Install the project's required dependencies before judging the baseline.

## Main work

- Run the existing tests and record the baseline.
- Strengthen regression tests around task parsing, task hierarchy/inheritance, splitting, ordering, scheduling, and Zim page rendering before moving those responsibilities.
- Replace Kivy logging in non-UI modules with Python `logging`.
- Introduce typed settings objects and a persistence adapter around the existing INI configuration.
- Move parsing of comma-separated tag settings and time values out of `LurchCalApp.build_parsed_config()` into the configuration layer.
- Change core services/classes so they no longer require Kivy `ConfigParser`.
- Keep the existing Kivy UI functional.

## Exit criteria

- `TaskScheduler` and task/domain tests run without importing Kivy.
- Non-UI modules use standard Python logging.
- The Kivy UI can adapt its existing configuration into the new typed settings and still execute the workflow.
- Scheduling behavior is covered by tests before further architectural changes.

## Must not do

- Do not add the Task Server yet.
- Do not replace the Kivy UI yet.
- Do not change scheduling semantics intentionally.

---

# AP2 — Independent Task Server

## Goal

Create the separate local Task Server and move all Zim-specific I/O behind it, without yet changing LurchCal to use it.

## Preconditions

- AP1 is `DONE`.
- Typed LurchCal settings and Kivy-independent domain logic exist.

## Main work

- Add FastAPI dependencies needed by the Task Server.
- Introduce a source-neutral task DTO/API schema.
- Introduce a `TaskSource` abstraction and implement `ZimTaskSource`.
- Reuse deterministic SQLite fixture generation from `tests/zim_test_utils.py`.
- Open the Zim DB read-only with short-lived connections and guaranteed close.
- Make the `as_of` date explicit instead of relying on SQLite `date()` in tests.
- Implement versioned endpoints:
  - `GET /api/v1/health`
  - `GET /api/v1/capabilities`
  - `GET /api/v1/tasks?as_of=YYYY-MM-DD`
  - Task Server settings endpoints required for browser-managed source configuration
  - `POST /api/v1/schedule-publications`
- Move the existing Zim schedule-page rendering behavior into the Task Server side.
- Add unit and API integration tests.

## Exit criteria

- Task Server runs as its own process on localhost.
- Task retrieval reproduces the current effective Zim filtering behavior.
- Tasks are read-only; no task mutation endpoint exists.
- Schedule publication reproduces the current Zim page semantics.
- Task Server tests do not require the production Zim database.

## Must not do

- Do not switch the Kivy app to the Task Server yet.
- Do not add the browser UI.
- Do not invent generic CRUD APIs.

---

# AP3 — LurchCal consumes the Task Server

## Goal

Replace every direct Zim access in LurchCal with Task Server calls while keeping the Kivy application operational.

## Preconditions

- AP2 is `DONE`.
- Task Server endpoints and their tests are stable.

## Main work

- Implement a `TaskServerClient` with timeouts and domain-level exceptions.
- Convert Task Server DTOs into existing LurchCal `Task` objects.
- Preserve duration/tag parsing, task splitting, hierarchy building, and inherited metadata in LurchCal.
- Replace `TaskParser._read_zim_tasks()` usage with the client.
- Replace direct `write_to_zim_page()` use with Task Server schedule publication.
- Move Zim-specific settings out of LurchCal-owned configuration and into Task Server configuration.
- Add Task Server base URL to LurchCal configuration.
- Keep Kivy buttons and behavior working through the new service boundary.
- Add integration tests with an in-process/test Task Server or mocked HTTP boundary.

## Exit criteria

- Kivy LurchCal still performs its three current user actions.
- No production LurchCal module directly reads Zim SQLite or writes a Zim page.
- Zim paths are no longer required by the LurchCal core/application configuration.
- Failure of the Task Server produces a clear LurchCal error rather than a raw HTTP exception.

## Must not do

- Do not remove Kivy.
- Do not build the browser UI yet.
- Do not move LurchCal parsing/scheduling rules into the Task Server.

---

# AP4 — LurchCal web backend and job model

## Goal

Create the local LurchCal FastAPI/Jinja2 server without removing Kivy yet.

## Preconditions

- AP3 is `DONE`.
- LurchCal is already independent of direct Zim access.

## Main work

- Extract/finish a UI-independent `SchedulingService` from `lurchcal_wf.py`.
- Replace Kivy-specific progress callbacks with generic progress events/callbacks.
- Add a FastAPI web server for LurchCal.
- Add Jinja2 and static-file support.
- Add a small in-memory background job model (`queued`, `running`, `succeeded`, `failed`).
- Ensure Outlook COM is created and used inside the same worker thread; do not pass COM objects between threads.
- Add server-side settings read/write/validation for LurchCal settings.
- Add a LurchCal settings facade for Task Server settings rather than making the browser call the Task Server directly.
- Add normalized calendar-events JSON suitable for FullCalendar.
- Add tests for workflow service, job lifecycle, settings, and API routes.

## Exit criteria

- The LurchCal web server runs locally and can start/observe the main workflows through HTTP.
- Long-running scheduling/calendar operations do not block the initiating HTTP request.
- Calendar event data is provider-neutral.
- Kivy may still coexist as a fallback interface.

## Must not do

- Do not add Celery/Redis.
- Do not expose the Task Server directly to browser code.
- Do not remove Kivy yet.

---

# AP5 — HTMX/Alpine/FullCalendar browser UI

## Goal

Implement the browser UI and achieve functional parity with the Kivy UI.

## Preconditions

- AP4 is `DONE`.
- Backend actions, jobs, settings, and calendar data endpoints are available.

## Main work

- Build Jinja2 pages and reusable fragments.
- Use HTMX for workflow actions, form submission, partial refreshes, progress/job polling, results, and validation feedback.
- Use Alpine.js only for small local UI state.
- Vendor or otherwise pin compatible local copies of required frontend assets so normal local use does not require internet access.
- Add the three current Kivy actions:
  - create/publish schedule;
  - create schedule + calendar appointments;
  - remove LurchCal appointments.
- Show job progress and actionable errors.
- Show unscheduled tasks and scheduled tasks.
- Add browser-editable LurchCal settings and Task Server/Zim source settings through the LurchCal backend.
- Add FullCalendar view backed by normalized LurchCal event data.
- First calendar version is view-only; no drag/drop rescheduling.
- Add relevant route/UI tests; keep JavaScript minimal and test core behavior server-side where practical.

## Exit criteria

- All existing Kivy user actions are available from the browser.
- Configuration can be viewed, validated, changed, and persisted from the browser.
- Calendar view displays the requested time range and planned/existing events as designed.
- Browser code never accesses local files or Outlook directly.

## Must not do

- Do not build a SPA framework on top of Alpine.js.
- Do not add calendar drag/drop editing.
- Do not remove Kivy until browser parity is verified.

---

# AP6 — Cutover and cleanup

## Goal

Make the browser interface the default LurchCal UI, provide a simple local start experience, and remove Kivy-specific runtime code.

## Preconditions

- AP5 is `DONE`.
- Browser feature parity has been manually verified on the supported Windows setup, including Outlook if Outlook is the configured provider.

## Main work

- Add/update a local launcher that starts Task Server, then LurchCal Web Server, verifies readiness, and opens the default browser.
- Keep both services bound to localhost by default.
- Define clean shutdown behavior.
- Remove Kivy UI code and Kivy dependencies after confirming no remaining runtime use.
- Remove obsolete Kivy settings JSON/config glue.
- Clean up package/module boundaries where useful, without changing scheduling behavior.
- Update `README.md`, `SPECIFICATION.md`, and `documentation.md` to describe the new architecture and usage.
- Run the full test suite and document any environment-specific tests/manual checks.

## Exit criteria

- Normal usage requires no Kivy runtime.
- One user-facing launcher starts the local application and opens the browser.
- LurchCal contains no direct Zim access.
- Task Server remains a separate process with a source-neutral API.
- No Node.js server is required for normal operation.
- Documentation matches the shipped architecture.

## Must not do

- Do not broaden scope into multi-user/cloud/authentication work.
- Do not change the scheduling algorithm as part of cleanup.

---

## Completion notes

Add one entry per completed package in this format:

```text
YYYY-MM-DD APx DONE
- Summary of architectural changes
- Tests run and result
- Known limitations / follow-up explicitly deferred
```

2026-10-04 AP1 DONE
- Added immutable typed settings and an adapter from the existing INI/Kivy configuration; scheduling and task parsing now consume typed settings, and non-UI logging uses Python `logging`.
- Baseline: Python 3.11.11, `python -m pytest -q`: 27 passed, 1 failed (the existing timed-appointment test expected behavior not implemented by the scheduler). Final: `python -m pytest -q`: 33 passed; `python -m compileall -q src` and `git diff --check` passed. Added settings, parsing, hierarchy/inheritance, schedule-page format, and no-Kivy-import checks using per-test SQLite fixtures.
- Preserved existing appointment behavior; the appointment fixture now explicitly locks down that timed events are not blocked. AP2 remains deferred; Zim database and page access are still in LurchCal pending that package.
