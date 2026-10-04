from datetime import datetime
from fastapi.testclient import TestClient

from lurchcal.jobs import JobManager
from lurchcal.web_app import create_app, normalize_calendar_event
from lurchcal.web_settings import LurchCalSettings, LurchCalSettingsStore


def test_settings_round_trip_validation(tmp_path):
    store = LurchCalSettingsStore(tmp_path / "settings.ini")
    settings = LurchCalSettings(task_server_url="http://127.0.0.1:8999",
                                calendar_provider="google", days_for_scheduling=10)
    store.save(settings)
    assert store.load() == settings


def test_jobs_capture_progress_result_and_failure():
    manager = JobManager()

    def operation(progress):
        progress({"stage": "step", "percent": 50})
        return {"scheduled_tasks": [], "unscheduled_tasks": [], "warnings": [], "statistics": {"count": 0}}

    job = manager.submit(operation)
    deadline = __import__("time").monotonic() + 5
    while job.status in {"queued", "running"} and __import__("time").monotonic() < deadline:
        __import__("time").sleep(.01)
    assert job.status == "succeeded"
    assert job.progress[0]["stage"] == "step"
    assert job.result["statistics"]["count"] == 0

    failed = manager.submit(lambda progress: (_ for _ in ()).throw(RuntimeError("broken")))
    import time
    deadline = time.monotonic() + 5
    while failed.status in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(.01)
    assert failed.status == "failed"
    assert failed.error == "broken"


def test_workflow_dataclass_serializes_to_structured_job_result():
    from lurchcal.lurchcal_wf import WorkflowResult

    manager = JobManager()
    job = manager.submit(lambda progress: WorkflowResult([], [], ["warning"], {"total": 0}))
    import time
    deadline = time.monotonic() + 5
    while job.status in {"queued", "running"} and time.monotonic() < deadline:
        time.sleep(.01)
    assert job.result == {"scheduled_tasks": [], "unscheduled_tasks": [],
                          "warnings": ["warning"], "statistics": {"total": 0}}


def test_calendar_event_normalization():
    class Converted:
        summary = "meeting"
        parsedDateTime_start = datetime(2026, 10, 4, 9)
        parsedDateTime_end = datetime(2026, 10, 4, 10)
        all_day_event = False

    class Calendar:
        def convert_appointment(self, event):
            return Converted()

    event = normalize_calendar_event(object(), Calendar())
    assert event["title"] == "meeting"
    assert event["start"] == "2026-10-04T09:00:00"
    assert event["source"] == "calendar"


def test_http_health_pages_settings_and_task_server_proxy(tmp_path):
    class TaskClient:
        def _request(self, method, endpoint, **kwargs):
            if endpoint.endswith("settings") and method == "GET":
                return {"path_db": "db", "path_page": "page"}
            return {"valid": True, "errors": []}

        def health(self):
            return {"status": "ok"}

    app = create_app(settings_path=tmp_path / "app.ini", task_settings_client=TaskClient(),
                     job_manager=JobManager())
    with TestClient(app) as client:
        assert client.get("/api/v1/health").json() == {"status": "ok"}
        assert "AP5" in client.get("/").text
        assert client.get("/api/v1/settings/task-source").json()["path_db"] == "db"
        saved = client.put("/api/v1/settings/lurchcal", json={
            "task_server_url": "http://127.0.0.1:8001", "calendar_provider": "outlook",
            "days_for_scheduling": 12,
        })
        assert saved.status_code == 200
        assert client.post("/api/v1/settings/task-source/validate", json={}).json()["valid"]


def test_calendar_events_route_uses_worker_and_returns_normalized_values(tmp_path):
    from datetime import datetime

    class Event:
        summary = "appointment"
        parsedDateTime_start = datetime(2026, 10, 4, 9)
        parsedDateTime_end = datetime(2026, 10, 4, 10)
        all_day_event = False

    class Calendar:
        def authenticate(self):
            pass

        def get_appointments(self, start, end):
            return [object()]

        def convert_appointment(self, event):
            return Event()

    class Factory:
        @staticmethod
        def create_calendar(provider):
            return Calendar()

    app = create_app(settings_path=tmp_path / "calendar.ini", calendar_factory=Factory)
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events", params={
            "start": "2026-10-04T00:00:00", "end": "2026-10-05T00:00:00"})
    assert response.status_code == 200
    assert response.json()[0]["title"] == "appointment"
