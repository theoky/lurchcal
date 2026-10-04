"""Typed, UI-independent settings and adapter for the existing INI config."""
from configparser import ConfigParser as IniConfigParser
from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol


class ConfigReader(Protocol):
    def get(self, section: str, option: str) -> str: ...
    def getint(self, section: str, option: str) -> int: ...


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(","))


def _read_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError):
        return time(12, 0)


@dataclass(frozen=True)
class AppointmentSettings:
    min_task_len_4_appt: int
    lunch_break: int
    short_break: int
    short_break_after_ilm: int
    days_for_scheduling: int
    lunch_break_time: time
    before_noon_break_time: time
    start_of_day: time
    hours_per_day: int
    app: str


@dataclass(frozen=True)
class TaskSettings:
    def_task_len: int
    min_task_split: int


@dataclass(frozen=True)
class TagSettings:
    ilm: str
    tag_order: tuple[str, ...]
    tag_projects: tuple[str, ...]
    tag_ignore_appt: tuple[str, ...]
    tags_to_create_appt: tuple[str, ...]
    tags_future: tuple[str, ...]
    tags_to_block_time: tuple[str, ...]


@dataclass(frozen=True)
class ZimSettings:
    path_db: str
    path_page: str


@dataclass(frozen=True)
class AppSettings:
    appt: AppointmentSettings
    tasks: TaskSettings
    tags: TagSettings
    zim: ZimSettings


def settings_from_config(config: ConfigReader) -> AppSettings:
    """Adapt an existing Kivy or stdlib ConfigParser to typed settings."""
    getint = config.getint
    get = config.get
    return AppSettings(
        appt=AppointmentSettings(
            min_task_len_4_appt=getint("appt", "min_task_len_4_appt"),
            lunch_break=getint("appt", "lunch_break"),
            short_break=getint("appt", "short_break"),
            short_break_after_ilm=getint("appt", "short_break_after_ilm"),
            days_for_scheduling=getint("appt", "days_for_scheduling"),
            lunch_break_time=_read_time(get("appt", "lunch_break_time")),
            before_noon_break_time=_read_time(get("appt", "before_noon_break_time")),
            start_of_day=_read_time(get("appt", "start_of_day")),
            hours_per_day=getint("appt", "hours_per_day"),
            app=get("appt", "app").lower(),
        ),
        tasks=TaskSettings(
            def_task_len=getint("tasks", "def_task_len"),
            min_task_split=getint("tasks", "min_task_split"),
        ),
        tags=TagSettings(
            ilm=get("tags", "ilm"),
            tag_order=_split(get("tags", "tag_order")),
            tag_projects=_split(get("tags", "tag_projects")),
            tag_ignore_appt=_split(get("tags", "tag_ignore_appt")),
            tags_to_create_appt=_split(get("tags", "tags_to_create_appt")),
            tags_future=_split(get("tags", "tags_future")),
            tags_to_block_time=_split(get("tags", "tags_to_block_time")),
        ),
        zim=ZimSettings(
            path_db=get("zim", "path_db"), path_page=get("zim", "path_page")
        ),
    )


def read_settings(path: str) -> AppSettings:
    """Read the existing INI persistence format using the standard library."""
    config = IniConfigParser()
    if not config.read(path):
        raise FileNotFoundError(path)
    return settings_from_config(config)