"""Test fixtures for generating deterministic Zim task databases."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence, Tuple

DEFAULT_PAGES: Sequence[Tuple[int, str]] = (
    (1, "Work"),
    (2, "Personal"),
)

DEFAULT_TASK_ROWS: Sequence[Tuple[int, int, int, int, int, int, int, int, str, str, str, str]] = (
    (
        1,
        1,
        0,
        0,
        0,
        0,
        3,
        0,
        "2000-01-01",
        "2024-01-02",
        "deep",
        "Long Focus Task ~2h~ @Deep",
    ),
    (
        2,
        1,
        0,
        0,
        0,
        0,
        1,
        0,
        "2000-01-01",
        "2024-01-01",
        "",
        "Write summary",
    ),
    (
        3,
        2,
        0,
        0,
        0,
        0,
        2,
        1,
        "2000-01-01",
        "2024-01-04",
        "",
        "Waiting Task",
    ),
)


def initialize_zim_sqlite(
    db_path: Path,
    *,
    task_rows: Iterable[Sequence] | None = None,
    pages: Iterable[Sequence] | None = None,
) -> Path:
    """Create a SQLite database that mimics Zim's task schema."""

    db_path = Path(db_path)
    if db_path.exists():
        db_path.unlink()

    rows = tuple(task_rows or DEFAULT_TASK_ROWS)
    page_rows = tuple(pages or DEFAULT_PAGES)

    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE pages (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE tasklist (
                id INTEGER PRIMARY KEY,
                source INTEGER,
                parent INTEGER,
                haschildren BOOLEAN,
                hasopenchildren BOOLEAN,
                status INTEGER,
                prio INTEGER,
                waiting BOOLEAN,
                start TEXT,
                due TEXT,
                tags TEXT,
                description TEXT
            )
            """
        )
        cursor.executemany("INSERT INTO pages (id, name) VALUES (?, ?)", page_rows)
        cursor.executemany(
            """
            INSERT INTO tasklist (
                id,
                source,
                parent,
                haschildren,
                hasopenchildren,
                status,
                prio,
                waiting,
                start,
                due,
                tags,
                description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        connection.commit()

    return db_path


__all__ = ["initialize_zim_sqlite", "DEFAULT_TASK_ROWS", "DEFAULT_PAGES"]
