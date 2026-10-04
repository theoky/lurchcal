"""Local LurchCal FastAPI/Jinja2 backend (AP4; browser feature UI is AP5)."""
from datetime import datetime
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from starlette.requests import Request

from lurchcal.CalendarFactory import CalendarFactory
from lurchcal.TaskServerClient import TaskServerClient
from lurchcal.jobs import JobManager
from lurchcal.lurchcal_wf import SchedulingService
from lurchcal.web_settings import LurchCalSettings, LurchCalSettingsStore

logger = logging.getLogger(__name__)
BASE = Path(__file__).resolve().parent


class ScheduleRequest(BaseModel):
    create_calendar_appointments: bool = False
    publish_schedule: bool = True


class CalendarEvent(BaseModel):
    id: str
    title: str
    start: str
    end: str
    allDay: bool = False
    source: str = "calendar"


def normalize_calendar_event(event, calendar):
    converted = calendar.convert_appointment(event)
    if converted is None:
        return None
    start = converted.parsedDateTime_start
    end = converted.parsedDateTime_end
    title = converted.summary
    return {"id": f"calendar-{start.isoformat()}-{title}", "title": title,
            "start": start.isoformat(), "end": end.isoformat(),
            "allDay": bool(getattr(converted, "all_day_event", False)), "source": "calendar"}


def create_app(settings_path=None, task_settings_client=None, calendar_factory=None,
               job_manager=None):
    app = FastAPI(title="LurchCal", version="1.0.0")
    store = LurchCalSettingsStore(settings_path)
    app.state.settings_store = store
    app.state.jobs = job_manager or JobManager()
    app.state.calendar_factory = calendar_factory or CalendarFactory
    app.state.task_settings_client = task_settings_client
    templates = Jinja2Templates(directory=str(BASE / "templates"))
    static = BASE / "static"
    static.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

    def task_client(url=None):
        if app.state.task_settings_client is not None and url is None:
            return app.state.task_settings_client
        return TaskServerClient(url or store.load().task_server_url)

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html", context={})

    @app.get("/health")
    @app.get("/api/v1/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/v1/jobs/schedules", status_code=202)
    def submit_schedule(request: ScheduleRequest = None):
        request = request or ScheduleRequest()
        settings = store.app_settings()
        service = SchedulingService(settings, calendar_factory=app.state.calendar_factory)
        return app.state.jobs.submit(lambda progress: service.create_schedule(
            request.create_calendar_appointments, request.publish_schedule, progress)).as_dict()

    @app.post("/api/v1/jobs/remove-appointments", status_code=202)
    @app.post("/api/v1/jobs/calendar-appointment-removal", status_code=202)
    def submit_removal():
        service = SchedulingService(store.app_settings(), calendar_factory=app.state.calendar_factory)
        return app.state.jobs.submit(lambda progress: service.remove_calendar_appointments(progress)).as_dict()

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job.as_dict()

    @app.get("/api/v1/settings/lurchcal")
    def get_lurchcal_settings():
        return store.load()

    @app.put("/api/v1/settings/lurchcal")
    def save_lurchcal_settings(settings: LurchCalSettings):
        store.save(settings)
        return settings

    @app.post("/api/v1/settings/lurchcal/validate")
    def validate_lurchcal_settings(settings: LurchCalSettings):
        errors = []
        try:
            task_client(settings.task_server_url).health()
        except Exception as exc:
            errors.append(f"Task Server unavailable: {exc}")
        provider_available = True
        try:
            app.state.calendar_factory.create_calendar(settings.calendar_provider)
        except Exception as exc:
            provider_available = False
            errors.append(f"Calendar provider unavailable: {exc}")
        return {"valid": not errors, "errors": errors,
                "task_server_reachable": not any(e.startswith("Task Server") for e in errors),
                "calendar_provider_available": provider_available}

    @app.get("/api/v1/settings/task-source")
    def get_task_source_settings():
        return task_client()._request("GET", "/api/v1/settings", operation="settings retrieval")

    @app.put("/api/v1/settings/task-source")
    def save_task_source_settings(payload: dict):
        return task_client()._request("PUT", "/api/v1/settings", operation="settings update", json=payload)

    @app.post("/api/v1/settings/task-source/validate")
    def validate_task_source_settings(payload: dict | None = None):
        client = task_client()
        if payload is None:
            payload = client._request("GET", "/api/v1/settings", operation="settings retrieval")
        return client._request("POST", "/api/v1/settings/validate", operation="settings validation", json=payload)

    @app.get("/api/v1/settings/status")
    def settings_status():
        settings = store.load()
        try:
            task_client().health()
            reachable = True
            task_source = task_client()._request("GET", "/api/v1/settings", operation="settings retrieval")
            source_status = task_client()._request("POST", "/api/v1/settings/validate", operation="settings validation", json=task_source)
        except Exception as exc:
            reachable, source_status = False, {"valid": False, "errors": [str(exc)]}
        try:
            app.state.calendar_factory.create_calendar(settings.calendar_provider)
            calendar = {"available": True, "configured": True}
        except Exception as exc:
            calendar = {"available": False, "configured": False, "error": str(exc)}
        return {"task_server_reachable": reachable, "task_source": source_status, "calendar": calendar}

    @app.get("/api/v1/calendar/events", response_model=list[CalendarEvent])
    def calendar_events(start: datetime, end: datetime):
        if end <= start:
            raise HTTPException(status_code=422, detail="end must be later than start")
        def load_events():
            calendar = app.state.calendar_factory.create_calendar(store.load().calendar_provider)
            calendar.authenticate()
            result = []
            for event in calendar.get_appointments(start, end):
                try:
                    normalized = normalize_calendar_event(event, calendar)
                    if normalized:
                        result.append(normalized)
                except Exception:
                    logger.exception("Unable to normalize calendar event")
            return result
        return app.state.jobs.run_in_worker(load_events)

    return app


app = create_app()