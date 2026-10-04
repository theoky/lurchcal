# Contribution Guidelines for LurchCal

## Scope
These rules apply to the entire repository unless a nested `AGENTS.md` overrides them.

## Migration architecture contract

Before making architectural changes, read `ARCHITECTURE.md` and `MIGRATION.md`.

During the current migration:

- Preserve existing scheduling semantics unless a task explicitly asks to change them.
- LurchCal must not gain new direct Zim dependencies. The target architecture isolates all Zim database/page access in the separate Task Server.
- Task resources exposed by the Task Server are read-only. Do not add task create/update/delete endpoints unless the architecture is explicitly changed first.
- Schedule publication is a separate capability and may write the generated schedule through the configured task source.
- The Task Server is a separate local process.
- Both the Task Server and LurchCal Web Server bind to `127.0.0.1` by default.
- The browser communicates with the LurchCal Web Server, not directly with the Task Server.
- Scheduling/domain code must not depend on Kivy, FastAPI, Jinja2, HTMX, Alpine.js, or FullCalendar.
- Platform-specific calendar dependencies must remain inside calendar adapters or narrow platform integration boundaries.
- Keep Kivy functional through AP3/AP4/AP5 as described in `MIGRATION.md`; remove it only during AP6 after browser parity is verified.
- Implement one migration work package at a time. Do not opportunistically start subsequent packages.

## Documentation Expectations
- Update `SPECIFICATION.md` whenever you modify the scheduling workflow, task parsing, calendar integrations, or service boundaries so the architecture description stays accurate.
- Keep narrative documentation in `README.md`, `documentation.md`, `SPECIFICATION.md`, and `ARCHITECTURE.md` free of inline source citations; reserve those for pull request descriptions or review commentary.
- When you add new user-facing functionality, extend the documentation with end-to-end usage notes before closing the task.
- When completing a migration work package, update its status and completion note in `MIGRATION.md`.

## Code Style and Quality
- Favor small, testable functions. When touching scheduling logic, add or update automated tests under `tests/` to cover new edge cases.
- Avoid adding platform-specific dependencies outside the calendar adapters; guard them behind provider checks.
- Use Python standard `logging` in non-UI/core/service code. Kivy logging may remain only in legacy Kivy UI code while that UI still exists.
- Keep configuration persistence separate from typed configuration consumed by domain/application code.
- Reuse the deterministic per-test SQLite fixture approach in `tests/zim_test_utils.py` and `tests/conftest.py`; do not add a shared mutable SQLite test database.

## Review and Tooling
- The documented runtime is Python 3.11. Use it for authoritative test results unless the project documentation is deliberately updated.
- Run available automated tests before requesting review. If a test suite is missing, environment-gated, or incomplete, document the gap in the final report/PR description.
- Keep configuration defaults in sync between the active persistence/configuration files and any typed settings/constants introduced in code.
- For migration work, verify the relevant exit criteria in `MIGRATION.md` before marking a package complete.
