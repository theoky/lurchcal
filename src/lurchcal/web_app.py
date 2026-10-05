"""Local LurchCal FastAPI/Jinja2 backend and AP5 browser interface."""
from datetime import datetime, timedelta
import logging
from pathlib import Path
from threading import Lock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from urllib.parse import parse_qs
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.requests import Request

from lurchcal.CalendarFactory import CalendarFactory
from lurchcal.TaskServerClient import TaskServerClient
from lurchcal.jobs import JobManager
from lurchcal.lurchcal_wf import SchedulingService
from lurchcal.web_settings import LurchCalSettings, LurchCalSettingsStore

logger = logging.getLogger(__name__)
BASE = Path(__file__).resolve().parent


def _friendly_error(exc):
    text = str(exc).strip()
    if "Invalid class string" in text or "-2147221005" in text:
        return "Outlook is unavailable. Install/configure Outlook or select Google Calendar in settings."
    if "Task Server" in text or "Connection" in type(exc).__name__:
        return "Task Server is unavailable. Start it and verify its address in settings."
    return text or "The operation failed. Check the server log for details."


def _read_source_settings(client_factory):
    try:
        return client_factory()._request("GET", "/api/v1/settings", operation="settings retrieval")
    except Exception:
        logger.exception("Unable to load Task Server source settings for browser page")
        return {"path_db": "", "path_page": ""}


async def _read_form(request):
    """Decode normal URL-encoded forms without requiring multipart support."""
    body = (await request.body()).decode("utf-8")
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


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


def normalize_calendar_event(event, calendar, display_timezone=None):
    converted = calendar.convert_appointment(event)
    if converted is None:
        return None
    start = converted.parsedDateTime_start
    end = converted.parsedDateTime_end
    # Outlook COM exposes appointment wall-clock fields. Depending on the Outlook
    # profile, pywin32 may attach a timezone whose offset does not describe those
    # displayed fields; preserve the fields and remove tzinfo rather than converting.
    outlook_wall_time = getattr(calendar, "uses_local_wall_time", False)
    if outlook_wall_time:
        if start.tzinfo is not None:
            start = start.replace(tzinfo=None)
        if end.tzinfo is not None:
            end = end.replace(tzinfo=None)
    elif display_timezone:
        target_timezone = ZoneInfo(display_timezone)
        if start.tzinfo is not None:
            start = start.astimezone(target_timezone).replace(tzinfo=None)
        if end.tzinfo is not None:
            end = end.astimezone(target_timezone).replace(tzinfo=None)
    logger.info(
        "Calendar event timestamps: adapter=%s source_start=%s source_start_tz=%s "
        "source_end=%s source_end_tz=%s display_timezone=%s api_start=%s api_end=%s",
        type(calendar).__name__, converted.parsedDateTime_start,
        getattr(converted.parsedDateTime_start, "tzinfo", None),
        converted.parsedDateTime_end, getattr(converted.parsedDateTime_end, "tzinfo", None),
        display_timezone, start.isoformat(), end.isoformat(),
    )
    title = converted.summary
    return {"id": f"calendar-{start.isoformat()}-{title}", "title": title,
            "start": start.isoformat(), "end": end.isoformat(),
            "allDay": bool(getattr(converted, "all_day_event", False)), "source": "calendar"}


def _in_visible_range(event, start, end):
    event_start = datetime.fromisoformat(event["start"])
    event_end = datetime.fromisoformat(event["end"])
    # Calendar API datetimes can be timezone-aware while scheduler times are local-naive.
    # FullCalendar supplies the range in the browser's timezone; normalize to naive local
    # wall time for comparison with the existing adapter's local-naive values.
    start, end = start.replace(tzinfo=None), end.replace(tzinfo=None)
    event_start, event_end = event_start.replace(tzinfo=None), event_end.replace(tzinfo=None)
    return event_start < end and event_end > start


def create_app(settings_path=None, task_settings_client=None, calendar_factory=None,
               job_manager=None):
    app = FastAPI(title="LurchCal", version="1.0.0")
    store = LurchCalSettingsStore(settings_path)
    app.state.settings_store = store
    app.state.jobs = job_manager or JobManager()
    app.state.calendar_factory = calendar_factory or CalendarFactory
    app.state.task_settings_client = task_settings_client
    app.state.workflow_lock = Lock()
    app.state.active_workflow = None
    app.state.planned_events = []
    templates = Jinja2Templates(directory=str(BASE / "templates"))
    static = BASE / "static"
    static.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

    def task_client(url=None):
        if app.state.task_settings_client is not None and url is None:
            return app.state.task_settings_client
        return TaskServerClient(url or store.load().task_server_url)

    def submit_ui_job(kind, operation):
        with app.state.workflow_lock:
            if app.state.active_workflow:
                raise RuntimeError("Another scheduling/calendar job is active. Wait for it to finish.")
            app.state.active_workflow = kind

        def run(progress):
            try:
                result = operation(progress)
                scheduled_items = getattr(result, "scheduled_tasks", None)
                if scheduled_items is None and isinstance(result, dict):
                    scheduled_items = result.get("scheduled_tasks")
                if scheduled_items is not None:
                    planned = []
                    for index, item in enumerate(scheduled_items):
                        if isinstance(item, dict):
                            start = datetime.fromisoformat(item["start"])
                            duration = item["duration"]
                            title = item.get("description", "Scheduled task")
                        else:
                            start, duration, title = item.start, item.duration, item.task.description
                        end = start + timedelta(minutes=duration)
                        planned.append({"id": f"planned-{index}-{start.isoformat()}",
                            "title": title, "start": start.isoformat(),
                            "end": end.isoformat(), "allDay": False, "source": "planned"})
                    app.state.planned_events = planned
                    app.state.last_schedule_result = {
                        "statistics": getattr(result, "statistics", {}) if not isinstance(result, dict) else result.get("statistics", {}),
                        "scheduled_tasks": getattr(result, "scheduled_tasks", []) if not isinstance(result, dict) else result.get("scheduled_tasks", []),
                        "unscheduled_tasks": getattr(result, "unscheduled_tasks", []) if not isinstance(result, dict) else result.get("unscheduled_tasks", []),
                    }
                return result
            except Exception as exc:
                logger.exception("Browser workflow job failed")
                friendly = _friendly_error(exc)
                if friendly == str(exc) or not friendly:
                    friendly = "The operation failed. Check settings and server logs for details."
                raise RuntimeError(friendly) from exc
            finally:
                with app.state.workflow_lock:
                    app.state.active_workflow = None

        try:
            job = app.state.jobs.submit(run)
            if job.status not in {"queued", "running"}:
                with app.state.workflow_lock:
                    app.state.active_workflow = None
            return job
        except Exception:
            with app.state.workflow_lock:
                app.state.active_workflow = None
            raise

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request=request, name="index.html", context={
            "settings": store.load(), "source": _read_source_settings(task_client),
            "last_result": getattr(app.state, "last_schedule_result", None),
        })

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        return templates.TemplateResponse(request=request, name="settings.html", context={
            "settings": store.load(), "source": _read_source_settings(task_client),
        })

    @app.get("/ui/tasks", response_class=HTMLResponse)
    def ui_tasks(request: Request):
        try:
            from datetime import date
            from lurchcal.TaskParser import TaskParser
            from lurchcal.lurchcal_wf import build_tree
            from bigtree import preorder_iter
            tasks = TaskParser(store.app_settings()).parse_tasks(task_client().get_tasks(date.today()))
            tree = build_tree(tasks)
            ordered = [node.get_attr("task") for node in preorder_iter(
                tree, filter_condition=lambda n: n.node_name != "0.0")]
            return templates.TemplateResponse(request=request, name="tasks.html", context={
                "tasks": [{"description": task.description} for task in ordered], "count": len(ordered)})
        except Exception as exc:
            logger.exception("Unable to load task overview")
            return templates.TemplateResponse(request=request, name="message.html", context={
                "message": "Unable to load tasks. " + _friendly_error(exc)}, status_code=503)

    @app.post("/ui/jobs/schedule", response_class=HTMLResponse)
    async def ui_schedule(request: Request):
        try:
            form = await _read_form(request)
            create_calendar_appointments = form.get("create_calendar_appointments", "false")
            request_data = ScheduleRequest(create_calendar_appointments=create_calendar_appointments == "true")
            settings = store.app_settings()
            service = SchedulingService(settings, calendar_factory=app.state.calendar_factory)
            job = submit_ui_job("schedule-and-calendar" if request_data.create_calendar_appointments else "publish-schedule", lambda progress: service.create_schedule(
                request_data.create_calendar_appointments, True, progress))
            return templates.TemplateResponse(request=request, name="job.html", context={"job": job.as_dict()}, status_code=202)
        except Exception as exc:
            logger.exception("Unable to start scheduling job")
            return templates.TemplateResponse(request=request, name="message.html", context={"message": _friendly_error(exc)}, status_code=400)

    @app.post("/ui/jobs/publish", response_class=HTMLResponse)
    def ui_publish(request: Request):
        try:
            service = SchedulingService(store.app_settings(), calendar_factory=app.state.calendar_factory)
            job = submit_ui_job("publish-schedule", lambda progress: service.create_schedule(False, True, progress))
            return templates.TemplateResponse(request=request, name="job.html", context={"job": job.as_dict()}, status_code=202)
        except Exception as exc:
            logger.exception("Unable to start schedule publication job")
            return templates.TemplateResponse(request=request, name="message.html", context={"message": _friendly_error(exc)}, status_code=400)

    @app.post("/ui/jobs/remove", response_class=HTMLResponse)
    def ui_remove(request: Request):
        try:
            service = SchedulingService(store.app_settings(), calendar_factory=app.state.calendar_factory)
            job = submit_ui_job("remove-calendar", lambda progress: service.remove_calendar_appointments(progress))
            return templates.TemplateResponse(request=request, name="job.html", context={"job": job.as_dict()}, status_code=202)
        except Exception as exc:
            logger.exception("Unable to start appointment removal job")
            return templates.TemplateResponse(request=request, name="message.html", context={"message": _friendly_error(exc)}, status_code=400)

    @app.get("/ui/results", response_class=HTMLResponse)
    def ui_results(request: Request):
        result = getattr(app.state, "last_schedule_result", None)
        return templates.TemplateResponse(request=request, name="results.html", context={"result": result})

    @app.get("/ui/jobs/{job_id}", response_class=HTMLResponse)
    def ui_job(request: Request, job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return templates.TemplateResponse(request=request, name="job.html", context={"job": job.as_dict()})

    @app.post("/ui/settings/save-and-test-lurchcal", response_class=HTMLResponse)
    async def ui_save_and_test_lurchcal(request: Request):
        try:
            form = await _read_form(request)
            # HTML omits unchecked checkboxes entirely.
            form.setdefault("short_break_after_ilm", "false")
            settings = LurchCalSettings(**form)
        except Exception as exc:
            return templates.TemplateResponse(request=request, name="message.html", context={"message": "Invalid settings: " + _friendly_error(exc)}, status_code=422)
        try:
            store.save(settings)
        except OSError as exc:
            logger.exception("Unable to save LurchCal settings")
            return templates.TemplateResponse(request=request, name="message.html", context={"message": "Settings could not be saved: " + _friendly_error(exc)}, status_code=500)
        try:
            result = validate_lurchcal_settings(settings)
            msg = "Settings saved and providers are available." if result["valid"] else "Settings saved, but validation failed: " + "; ".join(
                "Task Server is unavailable. Check its address and start the Task Server." if error.startswith("Task Server") else
                "Calendar provider is unavailable or not configured. Check the provider settings/authentication." if error.startswith("Calendar provider") else error
                for error in result["errors"])
        except Exception as exc:
            logger.exception("Unable to validate saved LurchCal settings")
            msg = "Settings saved, but validation could not complete: " + _friendly_error(exc)
        return templates.TemplateResponse(request=request, name="message.html", context={"message": msg})

    @app.post("/ui/settings/task-source", response_class=HTMLResponse)
    async def ui_save_source(request: Request):
        form = await _read_form(request)
        payload = {"path_db": form.get("path_db", ""), "path_page": form.get("path_page", "")}
        try:
            settings_client = task_client()
            result = settings_client._request("POST", "/api/v1/settings/validate", operation="settings validation", json=payload)
            if not result.get("valid"):
                return templates.TemplateResponse(request=request, name="message.html", context={"message": "Task source settings were not saved: " + "; ".join(result.get("errors", []))}, status_code=422)
            settings_client._request("PUT", "/api/v1/settings", operation="settings update", json=payload)
            text = "Task source settings saved and valid."
        except Exception as exc:
            logger.exception("Task source settings update failed")
            text = "Task Server/source settings could not be saved: " + _friendly_error(exc)
        return templates.TemplateResponse(request=request, name="message.html", context={"message": text})

    @app.post("/ui/settings/validate-source", response_class=HTMLResponse)
    async def ui_validate_source(request: Request):
        form = await _read_form(request)
        try:
            result = task_client()._request("POST", "/api/v1/settings/validate", operation="settings validation", json={"path_db": form.get("path_db", ""), "path_page": form.get("path_page", "")})
            text = "Task source is valid." if result.get("valid") else "Task source is invalid: " + "; ".join(result.get("errors", []))
        except Exception as exc:
            text = "Unable to validate Task Server/source: " + _friendly_error(exc)
        return templates.TemplateResponse(request=request, name="message.html", context={"message": text})

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
            logger.exception("Unable to read Task Server/source status")
            reachable, source_status = False, {"valid": False, "errors": [_friendly_error(exc)]}
        try:
            app.state.calendar_factory.create_calendar(settings.calendar_provider)
            calendar = {"available": True, "configured": True}
        except Exception as exc:
            logger.exception("Configured calendar provider is unavailable")
            calendar = {"available": False, "configured": False,
                        "error": "Calendar provider unavailable or not configured. Check settings/authentication."}
        return {"task_server_reachable": reachable, "task_source": source_status, "calendar": calendar}

    @app.get("/api/v1/calendar/events", response_model=list[CalendarEvent])
    def calendar_events(start: datetime, end: datetime,
                        time_zone: str | None = Query(default=None, alias="timeZone")):
        if end <= start:
            raise HTTPException(status_code=422, detail="end must be later than start")
        if time_zone:
            try:
                ZoneInfo(time_zone)
            except ZoneInfoNotFoundError as exc:
                raise HTTPException(status_code=422, detail="timeZone must be a valid IANA timezone") from exc
        def load_events():
            provider = store.load().calendar_provider
            calendar = app.state.calendar_factory.create_calendar(provider)
            calendar.authenticate()
            logger.info(
                "Calendar events request: provider=%s requested_timezone=%s "
                "range_start=%s range_end=%s adapter=%s",
                provider, time_zone, start.isoformat(), end.isoformat(),
                type(calendar).__name__,
            )
            result = []
            if provider == "google" and time_zone:
                appointments = calendar.get_appointments(start, end, response_timezone=time_zone)
            else:
                appointments = calendar.get_appointments(start, end)
            for event in appointments:
                try:
                    normalized = normalize_calendar_event(event, calendar, time_zone)
                    if normalized:
                        result.append(normalized)
                except Exception:
                    logger.exception("Unable to normalize calendar event")
            if provider == "outlook":
                try:
                    restriction = getattr(calendar, "last_restriction", "unknown")
                    logger.info(
                        "Outlook calendar diagnostics: restriction=%s result_count=%d "
                        "machine_timezone=%s",
                        restriction, len(result), datetime.now().astimezone().tzinfo,
                    )
                except Exception:
                    logger.debug("Unable to read Outlook calendar diagnostics", exc_info=True)
            result.extend(event for event in app.state.planned_events
                          if _in_visible_range(event, start, end))
            logger.info("Calendar events response: provider=%s events=%d", provider, len(result))
            return result
        return app.state.jobs.run_in_worker(load_events)

    return app


app = create_app()