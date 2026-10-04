"""Versioned, source-neutral API schemas."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskRead(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    parent_id: str | None = None
    description: str
    priority: int
    start_date: date | None = None
    due_date: date | None = None
    source_name: str | None = None
    has_children: bool


class TaskListResponse(BaseModel):
    tasks: list[TaskRead]


class CapabilitiesResponse(BaseModel):
    api_version: str = "v1"
    tasks_read_only: bool = True
    schedule_publication: bool = True


class TaskServerSettings(BaseModel):
    path_db: str = ""
    path_page: str = ""


class SettingsValidation(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class ScheduleItem(BaseModel):
    start: datetime
    duration: int
    priority: int = 0
    description: str
    tags: list[str] = Field(default_factory=list)
    source_name: str = ""


class SchedulePublicationRequest(BaseModel):
    scheduled_tasks: list[ScheduleItem]


class SchedulePublicationResponse(BaseModel):
    published: bool = True
    task_count: int
    path: str