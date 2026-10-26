# Changelog

## Browser application and Task Server migration

- Introduced a staged migration from the desktop application to a local browser application and separate Task Server.
- Added Task Server APIs for source-neutral task retrieval, settings and validation, health/capability reporting, and schedule publication.
- Isolated Zim task database and schedule-page access in the Task Server; schedule publication writes the generated schedule without adding task-mutation endpoints.
- Added the LurchCal FastAPI/Jinja2/HTMX browser workflow, background jobs and progress reporting, settings management, and a normalized, view-only calendar interface.
- Added Task Server client and workflow integration, local service entry points, and browser-side validation and error handling.
- Removed the legacy Kivy desktop UI after browser workflow migration.

## Scheduling, task handling, and calendar improvements

- Improved task parsing and scheduling, including future-tagged tasks, configurable ignored tags, and corrected handling of multi-day out-of-office appointments.
- Added optional grouping of consecutive default-duration tasks into private/free calendar appointments, with a setting to enable or disable the behavior.
- Added visibility in the calendar for grouped task appointments and reporting for tasks that violate deadlines.
- Added orange categorization for LurchCal appointments in Outlook and Tangerine coloring for Google Calendar events.
- Refined the browser layout and removed obsolete migration text from the interface and documentation.
- Expanded regression tests and updated architecture, specification, and usage documentation throughout the migration.
