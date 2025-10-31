# LurchCal Product Specification

## Vision and Scope
LurchCal is a desktop assistant that converts task data maintained in [Zim Desktop Wiki](https://zim-wiki.org/) into a concrete work schedule and optionally pushes the resulting focus blocks into a connected calendar. The application aims to automate the "create calendar events from tasks" workflow so that the user can defend focus time without manually copy/pasting tasks. The tool runs fully on the user’s machine to avoid cloud dependencies and currently targets Windows (Outlook) with experimental Google Calendar support. 

The immediate scope is:
- Parse actionable tasks from the user’s Zim task database.
- Generate a prioritized schedule that respects working hours, breaks, existing meetings, and simple tag-based rules.
- Persist the schedule back to Zim and, on demand, mirror it as calendar appointments.

Longer term the app should support richer task metadata, additional calendar providers, more advanced scheduling constraints, and guardrails for conflicting appointments.

## Architectural Overview
The system is a Kivy application (`src/LurchCalApp.py`) that orchestrates a workflow defined in `lurchcal/lurchcal_wf.py`. The workflow coordinates three subsystems:

1. **Task ingestion** – `TaskParser` reads Zim’s SQLite database, creates `Task` objects, and resolves hierarchical metadata such as inherited durations and tags. Tasks longer than the configured split threshold are broken into subtasks. 
2. **Scheduling** – `TaskScheduler` prepares `Day` buckets representing working time, blocks breaks and existing meetings, and assigns tasks according to priority/tag filters. Reserved slots become `ScheduledTask` instances that carry start time, duration, and source metadata. 
3. **Calendar integration** – A `Calendar` implementation, selected via `CalendarFactory`, retrieves current appointments and optionally creates or deletes LurchCal events. Outlook automation uses `win32com`, while Google Calendar relies on the REST API. 

`LurchCalApp` provides a minimal GUI with three actions: write a Zim schedule, create appointments, or remove previously generated appointments. Each action spawns a background thread, updates a progress bar through a callback, and renders unscheduled tasks in a `RecycleView`. 

## Data Flow
1. **Configuration** – On startup the app loads Kivy’s `ConfigParser` from `lurchal.ini` and merges defaults defined in `build_config`. Parsed helper fields (tag lists, break times) live in `self.parsed_config`. 
2. **Task retrieval** – `create_task_appointments` instantiates `TaskParser` with the user config, reads open tasks via `_read_zim_tasks`, builds a task tree with `build_tree`, and flattens it in priority order. Duration and tag metadata cascade from parent tasks to children. 
3. **Calendar snapshot** – The workflow authenticates to the selected provider, fetches upcoming events for the scheduling horizon, and filters out previously generated LurchCal meetings. 
4. **Scheduling** – `TaskScheduler.schedule_everything` builds `Day` objects for the planning window, blocks meetings and breaks, and then iteratively reserves time for tasks ordered by `filter_list` and configured `tag_order`. Remaining capacity is offered to "future" tagged tasks. 
5. **Outputs** – `write_to_zim_page` produces a Zim-formatted task list, grouping entries by day and embedding task metadata. When appointment creation is enabled, the calendar adapter deletes stale LurchCal items, then calls `create_appointments_4_tasks` to add new ones and tags each appointment with a LurchCal GUID for future cleanup. 

## Key Domain Rules
- **Task metadata** – Durations are parsed from `~duration~` fragments using `durations_nlp`. Missing durations fall back to `tasks.def_task_len`. Parent tasks distribute or assign durations to children based on flags. Tags prefixed with `@` drive filtering rules. 
- **Scheduling window** – The planner considers five working days beginning at the next non-weekend day after `start_date`, respecting `hours_per_day` and `start_of_day`. The first day blocks past time when scheduling "today". 
- **Prioritization** – Tasks are sorted by due date, priority, duration, and start date, then filtered in waves: ILM tasks, due tasks by priority, general priority, and others. Configured `tag_order` ensures certain tags are scheduled before the rest within each wave. Future-tagged tasks are postponed until the end. 
- **Calendar hygiene** – LurchCal appointments carry a GUID (`definitions.py`) so cleanup can safely delete only owned entries. Busy status is set according to tags indicating forced appointments or time blocking. 

## External Dependencies
- **Kivy** for GUI, configuration, and logging.
- **durations-nlp** for human-friendly duration parsing.
- **bigtree** for handling task hierarchies.
- **multisort** for deterministic multi-key sorting.
- **win32com**, **google-api-python-client**, and associated auth libraries for calendar integrations.

## Configuration Surface
- `settings_lurchcal.json` (loaded via Kivy settings) exposes defaults for task lengths, scheduling horizon, calendar provider, tag semantics, and Zim paths. Users edit these through the settings dialog launched from the main window. 

## Current Limitations
- Error handling is minimal; failures in background threads surface only as strings in the UI. Outlook-specific dependencies prevent cross-platform execution without guards. 
- Tests are largely absent despite the presence of a `tests` directory, and much of the scheduling logic depends on integration scenarios that are hard to simulate.
- Configuration assumes synchronous execution and blocking UI during heavy operations.

## Proposed Next Steps
1. **Automated regression coverage** – Introduce unit tests for `TaskParser` and `TaskScheduler` using fixture Zim databases to ensure scheduling rules remain deterministic. This will also enable CI automation.
2. **Robust error surfacing** – Wrap background workflow calls with structured exception reporting and user-facing notifications. Consider surfacing log files or status dialogs for Outlook/Google auth issues.
3. **Configuration validation** – Add startup checks for Zim paths, calendar connectivity, and tag settings, possibly through a dedicated settings page section with inline validation results.
4. **Calendar abstraction hardening** – Expand `Calendar` to cover recurring events and timezone handling, and ensure Google Calendar parity with Outlook features (busy state, appointment deletion safety).
5. **User workflow polish** – Provide schedule previews before committing changes, allow selective appointment creation, and offer CLI automation for headless execution to support cron-style runs.

## Feature Opportunities
- **Adaptive focus management** – Continuously evaluate completed work versus planned effort and reflow remaining tasks into the schedule, optionally nudging the user when spillover threatens high-priority commitments.
- **Task source federation** – Import tasks from additional systems such as Microsoft To Do, Trello, or Todoist and normalize them into the Zim-backed workflow, allowing users to centralize planning without abandoning their preferred capture tools.
- **Visual timeline dashboard** – Provide a Gantt-style view within the Kivy UI that overlays scheduled tasks, existing meetings, and flexibility buffers so that users can drag blocks to fine-tune their day before committing updates.
- **Scenario planning mode** – Allow the user to spin up alternative schedules (e.g., "deep work" versus "meeting-heavy" scenarios) by tweaking parameters like working hours, tag emphasis, or meeting acceptance, then compare outcomes before publishing.
- **Predictive assistance** – Analyze historical completion rates and meeting loads to recommend realistic workloads, flag overcommitted days, and suggest deferring or delegating tasks when capacity is exceeded.
