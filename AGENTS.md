# Contribution Guidelines for LurchCal

## Scope
These rules apply to the entire repository unless a nested `AGENTS.md` overrides them.

## Documentation Expectations
- Update `SPECIFICATION.md` whenever you modify the scheduling workflow, task parsing, or calendar integrations so the architecture description stays accurate.
- Keep narrative documentation in `README.md`, `documentation.md`, and `SPECIFICATION.md` free of inline source citations; reserve those for pull request descriptions or review commentary.
- When you add new user-facing functionality, extend the documentation with end-to-end usage notes before closing the task.

## Code Style and Quality
- Favor small, testable functions. When touching scheduling logic, add or update automated tests under `tests/` to cover new edge cases.
- Avoid adding platform-specific dependencies outside the calendar adapters; guard them behind provider checks.
- Preserve existing logging patterns (`kivy.logger.Logger`) and expand them with actionable context on errors.

## Review and Tooling
- Run available automated tests before requesting review. If a test suite is missing or incomplete, document the gap in the PR description.
- Keep configuration defaults in sync between `settings_lurchcal.json` and any new constants introduced in code.
