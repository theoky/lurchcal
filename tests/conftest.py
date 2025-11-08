import contextlib
import gc
import pathlib
import sqlite3
import sys

import pytest

from .zim_test_utils import initialize_zim_sqlite

ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="function")
def zim_task_rows():
    """Override in tests to customize the inserted Zim task rows."""

    return None


@pytest.fixture(scope="function")
def zim_pages():
    """Override in tests to customize the inserted Zim pages."""

    return None


@pytest.fixture(scope="function")
def db_path(tmp_path, zim_task_rows, zim_pages):
    """Per-test working SQLite database generated from deterministic fixtures."""

    dst = tmp_path / "test_db.sqlite"
    initialize_zim_sqlite(dst, task_rows=zim_task_rows, pages=zim_pages)
    return dst


@pytest.fixture(scope="function")
def db_conn(db_path):
    """sqlite3 connection to the per-test DB copy, with safe PRAGMAs."""
    conn = sqlite3.connect(str(db_path))
    try:
        # Better read concurrency; acceptable durability for tests
        with contextlib.suppress(sqlite3.Error):
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
    finally:
        with contextlib.suppress(Exception):
            conn.close()
        # Encourage handle release on Windows
        gc.collect()


@pytest.fixture(scope="function")
def ro_conn(db_path):
    """Read-only sqlite3 connection (no -journal/-wal files)."""
    uri = f"file:{pathlib.Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        yield conn
    finally:
        with contextlib.suppress(Exception):
            conn.close()
        gc.collect()


# Optional: SQLAlchemy engine fixture
try:
    import sqlalchemy as sa  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    sa = None


@pytest.fixture(scope="function")
def engine(db_path):
    """SQLAlchemy engine for the per-test DB copy, disposed after use."""
    if sa is None:
        pytest.skip("SQLAlchemy not installed")
    eng = sa.create_engine(f"sqlite:///{pathlib.Path(db_path).as_posix()}")
    try:
        with eng.connect() as c:
            with contextlib.suppress(Exception):
                c.exec_driver_sql("PRAGMA journal_mode=WAL;")
                c.exec_driver_sql("PRAGMA synchronous=NORMAL;")
        yield eng
    finally:
        # CRITICAL on Windows to release file handles
        eng.dispose()
        gc.collect()
