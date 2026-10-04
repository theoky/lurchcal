"""Tests for the independent Task Server and Zim task source."""
from datetime import date, datetime
from contextlib import closing
import sqlite3

from fastapi.testclient import TestClient
import pytest

from task_server.app import create_app
from task_server.models import ScheduleItem, TaskServerSettings
from task_server.source import (
    SourceConfigurationError,
    SourceUnavailableError,
    ZimTaskSource,
)
from .zim_test_utils import initialize_zim_sqlite


@pytest.fixture
def service_paths(tmp_path, db_path):
    page = tmp_path / "schedule.txt"
    config = tmp_path / "task_server.ini"
    return db_path, page, config


@pytest.fixture
def client(service_paths):
    db, page, config = service_paths
    app = create_app(config)
    test_client = TestClient(app)
    test_client.put(
        "/api/v1/settings",
        json={"path_db": str(db), "path_page": str(page)},
    )
    return test_client


def test_health_capabilities_and_readonly_contract(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/capabilities").json() == {
        "api_version": "v1",
        "tasks_read_only": True,
        "schedule_publication": True,
    }
    paths = {route.path for route in client.app.routes}
    assert not any("/tasks" in path and path != "/api/v1/tasks" for path in paths)


def test_tasks_filter_as_of_and_map_source_neutral_dtos(client):
    response = client.get("/api/v1/tasks", params={"as_of": "2024-01-01"})
    assert response.status_code == 200
    assert response.json() == {
        "tasks": [{
            "id": "2", "parent_id": None, "description": "Write summary",
            "priority": 1, "start_date": "2000-01-01", "due_date": "2024-01-01",
            "source_name": "Work", "has_children": False,
        }, {
            "id": "1", "parent_id": None, "description": "Long Focus Task ~2h~ @Deep",
            "priority": 3, "start_date": "2000-01-01", "due_date": "2024-01-02",
            "source_name": "Work", "has_children": False,
        }]
    }
    later = client.get("/api/v1/tasks", params={"as_of": "2024-01-02"}).json()["tasks"]
    assert [task["id"] for task in later] == ["2", "1"]
    assert "waiting" not in later[0]
    assert "tasklist" not in later[0]


def test_tasks_exclude_future_start_waiting_and_closed_rows(tmp_path):
    rows = [
        (10, 1, 0, 0, 0, 0, 1, 0, "2024-01-03", "2024-01-05", "", "Starts later"),
        (11, 1, 0, 0, 0, 0, 1, 1, "2020-01-01", "2024-01-05", "", "Waiting"),
        (12, 1, 0, 0, 0, 1, 1, 0, "2020-01-01", "2024-01-05", "", "Closed"),
        (13, 1, 0, 0, 0, 0, 1, 0, "2020-01-01", "2024-01-05", "", "Active"),
    ]
    db = initialize_zim_sqlite(tmp_path / "filtered.db", task_rows=rows)
    tasks = ZimTaskSource(TaskServerSettings(path_db=str(db), path_page="")).get_tasks(date(2024, 1, 2))
    assert [task.description for task in tasks] == ["Active"]


def test_zim_database_is_not_modified_by_reads(db_path):
    before = db_path.read_bytes()
    ZimTaskSource(TaskServerSettings(path_db=str(db_path), path_page="")).get_tasks(date(2024, 1, 2))
    assert db_path.read_bytes() == before


def test_settings_round_trip_and_validate(client, service_paths):
    db, page, _ = service_paths
    assert client.get("/api/v1/settings").json() == {
        "path_db": str(db), "path_page": str(page)
    }
    result = client.post(
        "/api/v1/settings/validate",
        json={"path_db": str(db), "path_page": str(page)},
    )
    assert result.json() == {"valid": True, "errors": []}


def test_missing_and_invalid_database_configuration(service_paths, tmp_path):
    missing_path = tmp_path / "not-found.db"
    source = ZimTaskSource(TaskServerSettings(path_db=str(missing_path), path_page=""))
    assert len(source.validate()) == 2
    with pytest.raises(SourceConfigurationError):
        source.get_tasks(date(2024, 1, 1))

    invalid_db = tmp_path / "invalid.db"
    with sqlite3.connect(invalid_db) as connection:
        connection.execute("CREATE TABLE other (id INTEGER)")
    invalid = ZimTaskSource(TaskServerSettings(path_db=str(invalid_db), path_page=""))
    assert any("required task tables" in error for error in invalid.validate())
    with pytest.raises(SourceConfigurationError):
        invalid.get_tasks(date(2024, 1, 1))

    invalid_pages = tmp_path / "invalid_pages.db"
    with sqlite3.connect(invalid_pages) as connection:
        connection.execute("CREATE TABLE tasklist (id INTEGER)")
        connection.execute("CREATE TABLE pages (id INTEGER, title TEXT)")
    bad_pages = ZimTaskSource(TaskServerSettings(path_db=str(invalid_pages), path_page=""))
    assert any("task schema" in error for error in bad_pages.validate())

    absent = ZimTaskSource(TaskServerSettings(path_db="", path_page=""))
    with pytest.raises(SourceConfigurationError):
        absent.get_tasks(date(2024, 1, 1))


def test_sqlite_reads_are_read_only_and_connections_are_released(db_path, tmp_path, monkeypatch):
    source = ZimTaskSource(TaskServerSettings(path_db=str(db_path), path_page=str(tmp_path / "page")))
    original_connect = source._connect_read_only
    opened = []

    class TrackedConnection:
        def __init__(self, connection):
            self.connection = connection
            self.closed = False

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def close(self):
            self.closed = True
            self.connection.close()

    def tracked_connect(path):
        tracked = TrackedConnection(original_connect(path))
        opened.append(tracked)
        return tracked

    monkeypatch.setattr(source, "_connect_read_only", tracked_connect)
    rows = source.get_tasks(date(2024, 1, 2))
    assert rows and opened[-1].closed
    # The read-only URI cannot mutate the database.
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        with closing(source._connect_read_only(db_path)) as connection:
            connection.execute("DELETE FROM tasklist")


def test_source_closes_connection_when_schema_validation_fails(tmp_path, monkeypatch):
    invalid_db = tmp_path / "invalid.db"
    with sqlite3.connect(invalid_db) as connection:
        connection.execute("CREATE TABLE other (id INTEGER)")
    source = ZimTaskSource(TaskServerSettings(path_db=str(invalid_db), path_page=""))
    original_connect = source._connect_read_only
    opened = []

    class TrackedConnection:
        def __init__(self, connection):
            self.connection = connection
            self.closed = False

        def __getattr__(self, name):
            return getattr(self.connection, name)

        def close(self):
            self.closed = True
            self.connection.close()

    def tracked_connect(path):
        tracked = TrackedConnection(original_connect(path))
        opened.append(tracked)
        return tracked

    monkeypatch.setattr(source, "_connect_read_only", tracked_connect)
    with pytest.raises(SourceConfigurationError):
        source.get_tasks(date(2024, 1, 2))
    assert opened[0].closed


def test_publication_renders_current_page_structure(client, service_paths):
    _, page, _ = service_paths
    response = client.post("/api/v1/schedule-publications", json={
        "scheduled_tasks": [{
            "start": "2024-01-02T09:00:00", "duration": 30, "priority": 2,
            "description": "Write report", "tags": ["work", "deep"], "source_name": "Work",
        }]
    })
    assert response.status_code == 200
    assert response.json()["published"] is True
    assert response.json()["task_count"] == 1
    text = page.read_text(encoding="utf-8")
    assert text.startswith("Content-Type: text/x-zim-wiki\nWiki-Format: zim 0.6\n")
    assert "====== Geplante Tasks ======" in text
    assert "===== 2024-01-02 =====" in text
    assert "* 2024-01-02 09:00:00, 30m, (2): Write report (work, deep), [[Work]]" in text


def test_publication_reports_target_error(client, service_paths, tmp_path):
    _, page, _ = service_paths
    client.put("/api/v1/settings", json={
        "path_db": str(service_paths[0]),
        "path_page": str(tmp_path / "directory-target"),
    })
    (tmp_path / "directory-target").mkdir()
    response = client.post("/api/v1/schedule-publications", json={"scheduled_tasks": []})
    assert response.status_code == 422
    assert "target is a directory" in response.json()["detail"]


def test_settings_validation_reports_missing_db_and_publication_directory(client, tmp_path):
    response = client.post("/api/v1/settings/validate", json={
        "path_db": str(tmp_path / "missing.db"),
        "path_page": str(tmp_path / "missing-dir" / "schedule.txt"),
    })
    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert any("does not exist" in error for error in response.json()["errors"])


def test_tasks_endpoint_distinguishes_missing_configuration(client):
    client.put("/api/v1/settings", json={"path_db": "", "path_page": ""})
    response = client.get("/api/v1/tasks", params={"as_of": "2024-01-02"})
    assert response.status_code == 422
    assert "not configured" in response.json()["detail"]


def test_tasks_endpoint_distinguishes_database_configuration_error(client, tmp_path):
    client.put("/api/v1/settings", json={
        "path_db": str(tmp_path / "missing.db"), "path_page": str(tmp_path / "page.txt")
    })
    response = client.get("/api/v1/tasks", params={"as_of": "2024-01-02"})
    assert response.status_code == 422
    assert "does not exist" in response.json()["detail"]


def test_schedule_render_accepts_fixed_clock():
    item = ScheduleItem(
        start=datetime(2024, 1, 2, 9), duration=30, description="Task"
    )
    rendered = ZimTaskSource.render_schedule([item], now=datetime(2024, 1, 1, 12))
    assert "Creation-Date: 2024-01-01T12:00:00" in rendered