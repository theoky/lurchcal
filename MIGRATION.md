# LurchCal Migration Status

## Status

The migration to the local browser application is complete. The browser is the supported LurchCal interface, and the Task Server remains a separate local process.

## Current architecture

- The browser UI uses FastAPI, Jinja2, HTMX, Alpine.js, and FullCalendar.
- Task retrieval and schedule publication use the separate Task Server.
- Task resources are read-only; publishing a generated schedule is a separate capability.
- Both services bind to loopback by default.

See `ARCHITECTURE.md` for design details and `README.md` and `documentation.md` for setup and usage.

## Verification record

The migration completion verification recorded Python 3.11.11 with `python -m pytest -q` reporting 91 passed and one Starlette/httpx deprecation warning. `python -m compileall -q src tests` and `git diff --check` passed at that time. Outlook and interactive Windows launcher verification were not performed in that session.