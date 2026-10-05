from datetime import datetime
from fastapi.testclient import TestClient

from lurchcal.jobs import JobManager
from lurchcal.web_app import create_app, normalize_calendar_event
from lurchcal.web_settings import LurchCalSettings, LurchCalSettingsStore


def test_settings_round_trip_validation(tmp_path):
    store = LurchCalSettingsStore(tmp_path / "settings.ini")
    settings = LurchCalSettings(task_server_url="http://127.0.0.1:8999",
        calendar_provider="google", days_for_scheduling=10, min_task_len_4_appt=20,
        lunch_break=40, short_break=12, short_break_after_ilm=False,
        lunch_break_time="12:30", before_noon_break_time="10:15", start_of_day="08:30",
        hours_per_day=8, def_task_len=7, min_task_split=45, ilm="ivy",
        tag_order="urgent, admin", tag_projects="project", tag_ignore_appt="focus",
        tags_to_create_appt="meeting", tags_future="later", tags_to_block_time="busy")
    store.save(settings)
    assert store.load() == settings
    app_settings = store.app_settings()
    assert app_settings.appt.min_task_len_4_appt == 20
    assert app_settings.appt.short_break_after_ilm == 0
    assert app_settings.appt.start_of_day.hour == 8
    assert app_settings.tasks.def_task_len == 7
    assert app_settings.tags.tag_order == ("urgent", "admin")
    assert app_settings.tags.tags_to_block_time == ("busy",)


def test_settings_defaults_match_legacy_config_defaults():
    settings = LurchCalSettings()
    assert (settings.min_task_len_4_appt, settings.lunch_break, settings.short_break,
            settings.short_break_after_ilm, settings.days_for_scheduling) == (15, 30, 15, True, 7)
    assert (settings.lunch_break_time, settings.before_noon_break_time, settings.start_of_day,
            settings.hours_per_day, settings.calendar_provider) == ("12:00", "10:00", "9:00", 9, "outlook")
    assert (settings.def_task_len, settings.min_task_split) == (6, 60)
    assert (settings.ilm, settings.tag_order, settings.tag_projects, settings.tag_ignore_appt,
            settings.tags_to_create_appt, settings.tags_future, settings.tags_to_block_time) == (
        "ilm", "akquise, legal, mail", "", "focus time, no ext.* appt.*, ^blocked$", "appt", "future", "block")


def test_settings_reject_invalid_time_and_negative_duration():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        LurchCalSettings(start_of_day="25:00")
    with pytest.raises(ValidationError):
        LurchCalSettings(lunch_break=-1)


def test_browser_app_settings_work_without_legacy_kivy_ini(tmp_path, monkeypatch):
    import lurchcal.web_settings as web_settings

    monkeypatch.setattr(web_settings, "__file__", str(tmp_path / "web_settings.py"))
    store = LurchCalSettingsStore(tmp_path / "web.ini")

    settings = store.app_settings()

    assert settings.appt.min_task_len_4_appt == 15
    assert settings.appt.lunch_break == 30
    assert settings.appt.short_break == 15
    assert settings.appt.days_for_scheduling == 7
    assert settings.tasks.def_task_len == 6
    assert settings.tasks.min_task_split == 60
    assert settings.task_server_url == "http://127.0.0.1:8001"


def test_browser_app_settings_preserve_legacy_options_and_fill_missing_ones(tmp_path, monkeypatch):
    import lurchcal.web_settings as web_settings

    (tmp_path / "pkg" / "lurchcal").mkdir(parents=True)
    (tmp_path / "pkg" / "lurchcal.ini").write_text(
        "[appt]\nlunch_break = 45\n\n[tasks]\ndef_task_len = 12\n", encoding="utf-8")
    monkeypatch.setattr(web_settings, "__file__", str(tmp_path / "pkg" / "lurchcal" / "web_settings.py"))
    store = LurchCalSettingsStore(tmp_path / "web.ini")

    settings = store.app_settings()

    assert settings.appt.lunch_break == 45
    assert settings.appt.min_task_len_4_appt == 15
    assert settings.tasks.def_task_len == 12
    assert settings.tasks.min_task_split == 60


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


def test_calendar_event_normalization_converts_provider_time_to_display_timezone():
    from datetime import timezone

    class Converted:
        summary = "meeting"
        parsedDateTime_start = datetime(2026, 10, 4, 9, tzinfo=timezone.utc)
        parsedDateTime_end = datetime(2026, 10, 4, 10, tzinfo=timezone.utc)
        all_day_event = False

    class Calendar:
        def convert_appointment(self, event):
            return Converted()

    event = normalize_calendar_event(object(), Calendar(), "Europe/Vienna")
    assert event["start"] == "2026-10-04T11:00:00"
    assert event["end"] == "2026-10-04T12:00:00"


def test_outlook_wall_clock_time_is_not_shifted_to_browser_timezone():
    class CalendarOutlook:
        uses_local_wall_time = True

        def convert_appointment(self, event):
            class Converted:
                summary = "outlook meeting"
                parsedDateTime_start = datetime(2026, 10, 5, 12, 30)
                parsedDateTime_end = datetime(2026, 10, 5, 13, 0)
                all_day_event = False
            return Converted()

    event = normalize_calendar_event(object(), CalendarOutlook(), "Europe/Vienna")

    assert event["start"] == "2026-10-05T12:30:00"
    assert event["end"] == "2026-10-05T13:00:00"


def test_outlook_normalization_logs_source_and_api_times(caplog):
    import logging

    class CalendarOutlook:
        uses_local_wall_time = True

        def convert_appointment(self, event):
            class Converted:
                summary = "private subject must not be logged"
                parsedDateTime_start = datetime(2026, 10, 5, 12, 30)
                parsedDateTime_end = datetime(2026, 10, 5, 13, 0)
                all_day_event = False
            return Converted()

    with caplog.at_level(logging.INFO, logger="lurchcal.web_app"):
        normalize_calendar_event(object(), CalendarOutlook(), "Europe/Vienna")

    assert "source_start=2026-10-05 12:30:00" in caplog.text
    assert "api_start=2026-10-05T12:30:00" in caplog.text
    assert "private subject must not be logged" not in caplog.text


def test_aware_outlook_times_are_converted_to_browser_wall_time():
    from datetime import timezone

    class CalendarOutlook:
        uses_local_wall_time = True

        def convert_appointment(self, event):
            class Converted:
                summary = "outlook meeting"
                parsedDateTime_start = datetime.fromisoformat("2026-10-05T12:30:00+00:00")
                parsedDateTime_end = datetime.fromisoformat("2026-10-05T14:30:00+00:00")
                all_day_event = False
            return Converted()

    event = normalize_calendar_event(object(), CalendarOutlook(), "Europe/Vienna")

    assert event["start"] == "2026-10-05T12:30:00"
    assert event["end"] == "2026-10-05T14:30:00"


def test_calendar_uses_local_timezone_and_24_hour_time_format():
    from pathlib import Path

    app_js = Path(__file__).parents[1] / "src" / "lurchcal" / "static" / "app.js"
    config = app_js.read_text(encoding="utf-8")

    assert "timeZone:'local'" in config
    assert "eventTimeFormat:{hour:'2-digit',minute:'2-digit',hour12:false}" in config
    assert "slotLabelFormat:{hour:'2-digit',minute:'2-digit',hour12:false}" in config


def test_open_task_list_is_rendered_in_scrollable_container(tmp_path, monkeypatch):
    import bigtree
    from lurchcal import lurchcal_wf
    from lurchcal.TaskParser import TaskParser

    class TaskClient:
        def get_tasks(self, as_of):
            return ["source-task"]

    class Task:
        description = "example task"

    class Node:
        node_name = "example"

        @staticmethod
        def get_attr(name):
            return Task()

    monkeypatch.setattr(TaskParser, "parse_tasks", lambda self, tasks: [Task()])
    monkeypatch.setattr(lurchcal_wf, "build_tree", lambda tasks: object())
    monkeypatch.setattr(bigtree, "preorder_iter", lambda tree, filter_condition: [Node()])
    app = create_app(settings_path=tmp_path / "settings.ini", task_settings_client=TaskClient())
    with TestClient(app) as client:
        response = client.get("/ui/tasks")

    assert response.status_code == 200
    assert 'class="task-list-scroll"' in response.text
    assert "example" in response.text


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
        assert "LurchCal" in client.get("/").text
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


def test_browser_pages_render_actions_settings_and_bundled_assets(tmp_path):
    class TaskClient:
        def _request(self, method, endpoint, **kwargs):
            if method == "GET":
                return {"path_db": r"C:\zim\index.db", "path_page": r"C:\zim\Schedule.txt"}
            return {"valid": True, "errors": []}

        def health(self):
            return {"status": "ok"}

    app = create_app(settings_path=tmp_path / "settings.ini", task_settings_client=TaskClient())
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "Create and publish schedule" in home.text
        assert "Create schedule and calendar appointments" in home.text
        assert "Remove LurchCal appointments" in home.text
        assert "htmx.min.js" in home.text and "alpine.min.js" in home.text
        settings = client.get("/settings")
        assert "C:\\zim\\index.db" in settings.text
        assert 'type="number"' in settings.text
        for asset in ("/static/htmx.min.js", "/static/alpine.min.js",
                      "/static/fullcalendar/index.global.min.js", "/static/app.js"):
            assert client.get(asset).status_code == 200


def test_browser_ui_jobs_poll_and_render_results(tmp_path):
    from lurchcal.jobs import Job

    class ImmediateJobs:
        def __init__(self):
            self.jobs = {}

        def submit(self, operation):
            job = Job(status="running")
            self.jobs[job.id] = job
            try:
                job.result = operation(lambda event: job.progress.append(event))
                from lurchcal.jobs import _serialize
                job.result = _serialize(job.result)
                job.status = "succeeded"
            except Exception as exc:
                job.error = str(exc)
                job.status = "failed"
            return job

        def get(self, job_id):
            return self.jobs.get(job_id)

    class TaskClient:
        def _request(self, method, endpoint, **kwargs):
            return {"path_db": "db", "path_page": "page"} if method == "GET" else {"valid": True, "errors": []}

        def health(self):
            return {"status": "ok"}

    class Service:
        def __init__(self, *args, **kwargs):
            pass

        def create_schedule(self, create_calendar_appointments, publish_schedule, progress):
            progress({"stage": "tasks", "message": "Retrieving tasks"})
            return {"scheduled_tasks": [], "unscheduled_tasks": [], "warnings": [],
                    "statistics": {"task_count": 0, "scheduled_count": 0}}

        def remove_calendar_appointments(self, progress):
            progress({"stage": "complete", "message": "Appointments removed"})

    import lurchcal.web_app as web_app
    original = web_app.SchedulingService
    web_app.SchedulingService = Service
    try:
        app = create_app(settings_path=tmp_path / "settings.ini", task_settings_client=TaskClient(),
                         job_manager=ImmediateJobs())
        with TestClient(app) as client:
            response = client.post("/ui/jobs/publish")
            assert response.status_code == 202
            assert "Job succeeded" in response.text
            assert "No unscheduled tasks" in response.text
            job_id = response.text.split('data-job-id="', 1)[1].split('"', 1)[0]
            assert "succeeded" in client.get(f"/ui/jobs/{job_id}").text
            assert client.post("/ui/jobs/remove").status_code == 202
    finally:
        web_app.SchedulingService = original


def test_calendar_events_include_planned_slots_only_in_requested_range(tmp_path):
    class Calendar:
        def authenticate(self):
            pass

        def get_appointments(self, start, end):
            return []

    class Factory:
        @staticmethod
        def create_calendar(provider):
            return Calendar()

    app = create_app(settings_path=tmp_path / "settings.ini", calendar_factory=Factory)
    app.state.planned_events = [
        {"id": "p1", "title": "Planned", "start": "2026-10-05T09:00:00",
         "end": "2026-10-05T10:00:00", "allDay": False, "source": "planned"},
        {"id": "p2", "title": "Outside", "start": "2026-10-06T09:00:00",
         "end": "2026-10-06T10:00:00", "allDay": False, "source": "planned"},
    ]
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events", params={
            "start": "2026-10-05T00:00:00", "end": "2026-10-06T00:00:00"})
    assert response.status_code == 200
    assert [event["title"] for event in response.json()] == ["Planned"]


def test_google_calendar_query_converts_local_range_to_utc(monkeypatch):
    from datetime import timezone
    from lurchcal import CalendarGoogle as google_module

    captured = {}

    class Request:
        def execute(self):
            return {"items": []}

    class Events:
        def list(self, **kwargs):
            captured.update(kwargs)
            return Request()

    class Service:
        def events(self):
            return Events()

    monkeypatch.setattr(google_module, "build", lambda *args, **kwargs: Service())

    calendar = google_module.CalendarGoogle()
    calendar.get_appointments(datetime(2026, 10, 5, 9), datetime(2026, 10, 5, 10))

    expected_start = datetime(2026, 10, 5, 9).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    expected_end = datetime(2026, 10, 5, 10).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    assert captured["timeMin"] == expected_start
    assert captured["timeMax"] == expected_end


def test_google_calendar_query_requests_browser_timezone(monkeypatch):
    from lurchcal import CalendarGoogle as google_module

    captured = {}

    class Request:
        def execute(self):
            return {"items": []}

    class Events:
        def list(self, **kwargs):
            captured.update(kwargs)
            return Request()

    class Service:
        def events(self):
            return Events()

    monkeypatch.setattr(google_module, "build", lambda *args, **kwargs: Service())
    google_module.CalendarGoogle().get_appointments(
        datetime(2026, 10, 5, 9), datetime(2026, 10, 5, 10), response_timezone="Europe/Vienna")

    assert captured["timeZone"] == "Europe/Vienna"


def test_google_calendar_parses_offsetless_times_using_event_timezone():
    from lurchcal.CalendarGoogle import CalendarGoogle

    calendar = CalendarGoogle()
    event = {
        "summary": "meeting",
        "transparency": "opaque",
        "start": {"dateTime": "2026-10-05T12:30:00", "timeZone": "Europe/Vienna"},
        "end": {"dateTime": "2026-10-05T13:00:00", "timeZone": "Europe/Vienna"},
    }

    converted = calendar.convert_appointment(event)

    assert converted.parsedDateTime_start.isoformat() == "2026-10-05T12:30:00+02:00"
    assert converted.parsedDateTime_end.isoformat() == "2026-10-05T13:00:00+02:00"


def test_calendar_events_pass_browser_timezone_to_google_adapter(tmp_path):
    captured = {}

    class Calendar:
        def authenticate(self):
            pass

        def get_appointments(self, start, end, response_timezone=None):
            captured["response_timezone"] = response_timezone
            return []

    class Factory:
        @staticmethod
        def create_calendar(provider):
            assert provider == "google"
            return Calendar()

    store = LurchCalSettingsStore(tmp_path / "settings.ini")
    store.save(LurchCalSettings(calendar_provider="google"))
    app = create_app(settings_path=tmp_path / "settings.ini", calendar_factory=Factory)
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events", params={
            "start": "2026-10-05T00:00:00", "end": "2026-10-06T00:00:00",
            "timeZone": "Europe/Vienna"})

    assert response.status_code == 200
    assert captured["response_timezone"] == "Europe/Vienna"


def test_calendar_endpoint_returns_local_wall_time_for_browser_timezone(tmp_path):
    class Converted:
        summary = "meeting"
        parsedDateTime_start = datetime.fromisoformat("2026-10-05T10:30:00+00:00")
        parsedDateTime_end = datetime.fromisoformat("2026-10-05T11:00:00+00:00")
        all_day_event = False

    class Calendar:
        def authenticate(self):
            pass

        def get_appointments(self, start, end, response_timezone=None):
            return [object()]

        def convert_appointment(self, event):
            return Converted()

    class Factory:
        @staticmethod
        def create_calendar(provider):
            return Calendar()

    store = LurchCalSettingsStore(tmp_path / "settings.ini")
    store.save(LurchCalSettings(calendar_provider="google"))
    app = create_app(settings_path=tmp_path / "settings.ini", calendar_factory=Factory)
    with TestClient(app) as client:
        response = client.get("/api/v1/calendar/events", params={
            "start": "2026-10-05T00:00:00", "end": "2026-10-06T00:00:00",
            "timeZone": "Europe/Vienna"})

    assert response.status_code == 200
    event = response.json()[0]
    assert event["start"] == "2026-10-05T12:30:00"
    assert event["end"] == "2026-10-05T13:00:00"


def test_conflicting_browser_workflow_is_guarded(tmp_path):
    class TaskClient:
        def _request(self, method, endpoint, **kwargs):
            return {"path_db": "db", "path_page": "page"} if method == "GET" else {"valid": True}

    app = create_app(settings_path=tmp_path / "settings.ini", task_settings_client=TaskClient())
    app.state.active_workflow = "publish-schedule"
    with TestClient(app) as client:
        response = client.post("/ui/jobs/remove")
    assert response.status_code == 400
    assert "Another scheduling/calendar job is active" in response.text


def test_browser_settings_validate_before_saving_and_proxy_errors(tmp_path):
    class TaskClient:
        def __init__(self):
            self.saved = False

        def _request(self, method, endpoint, **kwargs):
            if method == "GET":
                return {"path_db": "old.db", "path_page": "old.txt"}
            if endpoint.endswith("validate"):
                return {"valid": False, "errors": ["database path does not exist"]}
            self.saved = True
            return {}

        def health(self):
            return {"status": "ok"}

    task_client = TaskClient()
    app = create_app(settings_path=tmp_path / "settings.ini", task_settings_client=task_client)
    with TestClient(app) as client:
        failed = client.post("/ui/settings/task-source", data={"path_db": "bad", "path_page": "page"})
        assert failed.status_code == 422
        assert "not saved" in failed.text
        assert task_client.saved is False
        invalid = client.post("/ui/settings/save-and-test-lurchcal", data={"task_server_url": "bad", "calendar_provider": "other", "days_for_scheduling": "0"})
        assert invalid.status_code == 422
        assert "Invalid settings" in invalid.text
