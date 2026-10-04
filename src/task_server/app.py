"""FastAPI application factory for the standalone Task Server."""
from datetime import date
import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from .config import SettingsStore
from .models import (
    CapabilitiesResponse,
    SchedulePublicationRequest,
    SchedulePublicationResponse,
    SettingsValidation,
    TaskListResponse,
    TaskServerSettings,
)
from .source import SourceConfigurationError, SourceUnavailableError, ZimTaskSource

logger = logging.getLogger(__name__)


def create_app(config_path: str | Path | None = None) -> FastAPI:
    store = SettingsStore(config_path or os.environ.get("LURCHCAL_TASK_SERVER_CONFIG"))
    app = FastAPI(title="LurchCal Task Server", version="1.0.0")
    app.state.settings_store = store

    def source() -> ZimTaskSource:
        return ZimTaskSource(store.load())

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/capabilities", response_model=CapabilitiesResponse)
    def capabilities() -> CapabilitiesResponse:
        return CapabilitiesResponse()

    @app.get("/api/v1/tasks", response_model=TaskListResponse)
    def get_tasks(as_of: date) -> TaskListResponse:
        try:
            return TaskListResponse(tasks=source().get_tasks(as_of))
        except SourceConfigurationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except SourceUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    @app.get("/api/v1/settings", response_model=TaskServerSettings)
    def get_settings() -> TaskServerSettings:
        return store.load()

    @app.put("/api/v1/settings", response_model=TaskServerSettings)
    def put_settings(settings: TaskServerSettings) -> TaskServerSettings:
        try:
            store.save(settings)
        except OSError as exc:
            logger.exception("Unable to persist Task Server settings")
            raise HTTPException(status_code=500, detail="Unable to persist settings") from exc
        return settings

    @app.post("/api/v1/settings/validate", response_model=SettingsValidation)
    def validate_settings(settings: TaskServerSettings) -> SettingsValidation:
        errors = ZimTaskSource(settings).validate()
        return SettingsValidation(valid=not errors, errors=errors)

    @app.post("/api/v1/schedule-publications", response_model=SchedulePublicationResponse)
    def publish_schedule(request: SchedulePublicationRequest) -> SchedulePublicationResponse:
        try:
            path = source().publish_schedule(request.scheduled_tasks)
        except SourceConfigurationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except SourceUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        return SchedulePublicationResponse(task_count=len(request.scheduled_tasks), path=path)

    return app


app = create_app()