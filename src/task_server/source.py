"""Task source abstraction and the isolated Zim implementation."""
from contextlib import closing
from datetime import date, datetime
import logging
import os
import sqlite3
from pathlib import Path
from typing import Protocol

from .models import ScheduleItem, TaskRead, TaskServerSettings

logger = logging.getLogger(__name__)


class TaskSourceError(Exception):
    """Base error raised while accessing a configured task source."""


class SourceConfigurationError(TaskSourceError):
    """The source configuration is missing or unusable."""


class SourceUnavailableError(TaskSourceError):
    """The configured source is unavailable or has an invalid schema."""


class TaskSource(Protocol):
    def get_tasks(self, as_of: date) -> list[TaskRead]: ...
    def publish_schedule(self, tasks: list[ScheduleItem]) -> str: ...


class ZimTaskSource:
    REQUIRED_COLUMNS = {
        "id", "source", "parent", "haschildren", "status", "prio",
        "waiting", "start", "due", "description",
    }

    def __init__(self, settings: TaskServerSettings):
        self.settings = settings

    def _db_path(self) -> Path:
        if not self.settings.path_db.strip():
            raise SourceConfigurationError("Zim database path_db is not configured")
        path = Path(self.settings.path_db).expanduser()
        if not path.is_file():
            raise SourceConfigurationError(f"Zim database does not exist: {path}")
        if not os.access(path, os.R_OK):
            raise SourceConfigurationError(f"Zim database is not readable: {path}")
        return path

    def _connect_read_only(self, path: Path) -> sqlite3.Connection:
        try:
            return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        except sqlite3.Error as exc:
            raise SourceUnavailableError(f"Unable to open Zim database: {exc}") from exc

    def _validate_schema(self, connection: sqlite3.Connection) -> None:
        try:
            tables = {row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )}
            if not {"tasklist", "pages"}.issubset(tables):
                raise SourceConfigurationError("Zim database is missing required task tables")
            columns = {row[1] for row in connection.execute("PRAGMA table_info(tasklist)")}
            if not self.REQUIRED_COLUMNS.issubset(columns):
                missing = sorted(self.REQUIRED_COLUMNS - columns)
                raise SourceConfigurationError(
                    "Zim task schema is missing required columns: " + ", ".join(missing)
                )
            page_columns = {row[1] for row in connection.execute("PRAGMA table_info(pages)")}
            if "name" not in page_columns:
                raise SourceConfigurationError("Zim pages schema is missing required column: name")
        except TaskSourceError:
            raise
        except sqlite3.Error as exc:
            raise SourceUnavailableError(f"Unable to inspect Zim database schema: {exc}") from exc

    @staticmethod
    def _parse_task_date(value: str | None) -> date | None:
        """Parse a Zim task date, treating sentinels and malformed values as absent."""
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid Zim task date value %r", value)
            return None

    def get_tasks(self, as_of: date) -> list[TaskRead]:
        path = self._db_path()
        try:
            with closing(self._connect_read_only(path)) as connection:
                try:
                    self._validate_schema(connection)
                    rows = connection.execute(
                        """SELECT t.id, t.parent, t.description, t.prio, t.start, t.due,
                              p.name, t.haschildren
                       FROM tasklist AS t LEFT JOIN pages AS p ON t.source = p.id
                       WHERE t.status = 0 AND t.waiting = 0 AND t.start <= ?
                       ORDER BY t.due ASC, t.prio DESC, t.start ASC, t.id ASC""",
                        (as_of.isoformat(),),
                    ).fetchall()
                finally:
                    connection.rollback()
        except SourceConfigurationError:
            raise
        except SourceUnavailableError:
            raise
        except sqlite3.Error as exc:
            logger.exception("Zim task query failed")
            raise SourceUnavailableError(f"Unable to read Zim tasks: {exc}") from exc

        return [
            TaskRead(
                id=str(row[0]),
                parent_id=str(row[1]) if row[1] not in (None, 0, "0") else None,
                description=row[2],
                priority=int(row[3] or 0),
                start_date=self._parse_task_date(row[4]),
                due_date=self._parse_task_date(row[5]),
                source_name=row[6],
                has_children=bool(row[7]),
            )
            for row in rows
        ]

    def validate(self) -> list[str]:
        errors: list[str] = []
        try:
            path = self._db_path()
            with closing(self._connect_read_only(path)) as connection:
                try:
                    self._validate_schema(connection)
                finally:
                    connection.rollback()
        except TaskSourceError as exc:
            errors.append(str(exc))
        except sqlite3.Error as exc:
            errors.append(f"Unable to validate Zim database: {exc}")

        if not self.settings.path_page.strip():
            errors.append("Schedule page path_page is not configured")
        else:
            target = Path(self.settings.path_page).expanduser()
            parent = target.parent
            if not parent.is_dir():
                errors.append(f"Schedule page directory does not exist: {parent}")
            if target.exists() and (target.is_dir() or not os.access(target, os.W_OK)):
                errors.append(f"Schedule page is not writable: {target}")
            elif not target.exists() and not os.access(parent, os.W_OK):
                errors.append(f"Schedule page directory is not writable: {parent}")
        return errors

    @staticmethod
    def render_schedule(tasks: list[ScheduleItem], now: datetime | None = None) -> str:
        now = now or datetime.now()
        lines = [
            "Content-Type: text/x-zim-wiki",
            "Wiki-Format: zim 0.6",
            "Creation-Date: " + now.isoformat(),
            "",
            "====== Geplante Tasks ======",
            "Created " + str(now),
            "",
            f"{len(tasks)} Tasks geplant.",
            "",
        ]
        current_day = None
        for item in tasks:
            if current_day != item.start.date():
                current_day = item.start.date()
                lines.append(f"===== {current_day} =====")
            tags = ", ".join(item.tags)
            lines.append(
                f"* {item.start}, {item.duration}m, ({item.priority}): "
                f"{item.description} ({tags}), [[{item.source_name}]]"
            )
        return "\n".join(lines) + "\n"

    def publish_schedule(self, tasks: list[ScheduleItem]) -> str:
        if not self.settings.path_page.strip():
            raise SourceConfigurationError("Schedule page path_page is not configured")
        target = Path(self.settings.path_page).expanduser()
        if not target.parent.is_dir():
            raise SourceConfigurationError(f"Schedule page directory does not exist: {target.parent}")
        if target.exists() and target.is_dir():
            raise SourceConfigurationError(f"Schedule page target is a directory: {target}")
        try:
            target.write_text(self.render_schedule(tasks), encoding="utf-8")
        except OSError as exc:
            logger.exception("Schedule publication failed for %s", target)
            raise SourceUnavailableError(f"Unable to publish schedule to {target}: {exc}") from exc
        return str(target)


__all__ = [
    "SourceConfigurationError",
    "SourceUnavailableError",
    "TaskSource",
    "ZimTaskSource",
]