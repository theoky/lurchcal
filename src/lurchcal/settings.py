"""Typed, UI-independent settings and adapter for the existing INI config."""
from configparser import ConfigParser as IniConfigParser
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
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
class AppSettings:
    appt: AppointmentSettings
    tasks: TaskSettings
    tags: TagSettings
    task_server_url: str = "http://127.0.0.1:8001"


def settings_from_config(config: ConfigReader) -> AppSettings:
    """Adapt an existing Kivy or stdlib ConfigParser to typed settings."""
    getint = config.getint
    get = config.get

    def get_optional(section: str, option: str, fallback: str) -> str:
        try:
            return get(section, option)
        except Exception:
            return fallback

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
            app=get_optional("appt", "app", "outlook").lower(),
        ),
        tasks=TaskSettings(
            def_task_len=getint("tasks", "def_task_len"),
            min_task_split=getint("tasks", "min_task_split"),
        ),
        tags=TagSettings(
            ilm=get_optional("tags", "ilm", "ilm"),
            tag_order=_split(get_optional("tags", "tag_order", "")),
            tag_projects=_split(get_optional("tags", "tag_projects", "")),
            tag_ignore_appt=_split(get_optional("tags", "tag_ignore_appt", "")),
            tags_to_create_appt=_split(get_optional("tags", "tags_to_create_appt", "appt")),
            tags_future=_split(get_optional("tags", "tags_future", "future")),
            tags_to_block_time=_split(get_optional("tags", "tags_to_block_time", "block")),
        ),
        task_server_url=_read_task_server_url(config),
    )


def _read_task_server_url(config: ConfigReader) -> str:
    """Read the service URL; migrate only that value from old INI if present."""
    try:
        return config.get("taskserver", "base_url")
    except Exception:
        pass
    try:
        return config.get("task_server", "base_url")
    except Exception:
        pass
    try:
        return config.get("lurchcal", "task_server_url")
    except Exception:
        pass
    return "http://127.0.0.1:8001"


def read_settings(path: str) -> AppSettings:
    """Read the existing INI persistence format using the standard library."""
    config = IniConfigParser()
    if not config.read(path):
        raise FileNotFoundError(path)
    return settings_from_config(config)


def migrate_legacy_zim_settings(
    source_path: str | None, task_server_config_path: str
) -> bool:
    """One-time bridge: copy legacy [zim] paths into Task Server INI if unset."""
    if not source_path:
        return False
    legacy = IniConfigParser()
    if not legacy.read(source_path) or "zim" not in legacy:
        return False
    target = Path(task_server_config_path)
    server = IniConfigParser()
    if server.read(target, encoding="utf-8") and server.has_section("zim"):
        if server.get("zim", "path_db", fallback="").strip() or server.get(
            "zim", "path_page", fallback=""
        ).strip():
            return False
    if not server.has_section("zim"):
        server.add_section("zim")
    for key in ("path_db", "path_page"):
        if legacy.has_option("zim", key):
            server.set("zim", key, legacy.get("zim", key))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        server.write(stream)
    return True