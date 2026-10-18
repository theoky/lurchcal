"""Typed INI persistence for settings owned by the LurchCal web service."""
from configparser import ConfigParser
from datetime import datetime
import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from lurchcal.settings import AppSettings, settings_from_config


class LurchCalSettings(BaseModel):
    task_server_url: str = "http://127.0.0.1:8001"
    calendar_provider: str = "outlook"
    days_for_scheduling: int = Field(default=7, ge=1, le=90)
    min_task_len_4_appt: int = Field(default=15, ge=0)
    lunch_break: int = Field(default=30, ge=0)
    short_break: int = Field(default=15, ge=0)
    short_break_after_ilm: bool = True
    lunch_break_time: str = "12:00"
    before_noon_break_time: str = "10:00"
    start_of_day: str = "9:00"
    hours_per_day: int = Field(default=9, ge=1, le=24)
    def_task_len: int = Field(default=6, ge=1)
    min_task_split: int = Field(default=60, ge=1)
    ilm: str = "ilm"
    tag_order: str = "akquise, legal, mail"
    tag_projects: str = ""
    tags_to_ignore: str = "2private, 2privat"
    tag_ignore_appt: str = "focus time, no ext.* appt.*, ^blocked$"
    tags_to_create_appt: str = "appt"
    tags_future: str = "future"
    tags_to_block_time: str = "block"

    @field_validator("task_server_url")
    @classmethod
    def valid_task_server_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Task Server URL must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    @field_validator("calendar_provider")
    @classmethod
    def valid_provider(cls, value):
        value = value.lower()
        if value not in {"outlook", "google"}:
            raise ValueError("Calendar provider must be outlook or google")
        return value

    @field_validator("lunch_break_time", "before_noon_break_time", "start_of_day")
    @classmethod
    def valid_time(cls, value):
        try:
            datetime.strptime(value, "%H:%M")
            return value
        except ValueError:
            try:
                parsed = datetime.strptime(value, "%H:%M").time()
                return parsed.strftime("%H:%M")
            except ValueError as exc:
                raise ValueError("Time must use HH:MM (24-hour) format") from exc


def default_settings_path():
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "LurchCal" / "lurchcal.ini"


class LurchCalSettingsStore:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("LURCHCAL_CONFIG", default_settings_path()))

    def load(self):
        parser = ConfigParser()
        if self.path.exists():
            parser.read(self.path, encoding="utf-8")
        return LurchCalSettings(
            task_server_url=parser.get("taskserver", "base_url", fallback="http://127.0.0.1:8001"),
            calendar_provider=parser.get("appt", "app", fallback="outlook"),
            days_for_scheduling=parser.getint("appt", "days_for_scheduling", fallback=7),
            min_task_len_4_appt=parser.getint("appt", "min_task_len_4_appt", fallback=15),
            lunch_break=parser.getint("appt", "lunch_break", fallback=30),
            short_break=parser.getint("appt", "short_break", fallback=15),
            short_break_after_ilm=parser.getboolean("appt", "short_break_after_ilm", fallback=True),
            lunch_break_time=parser.get("appt", "lunch_break_time", fallback="12:00"),
            before_noon_break_time=parser.get("appt", "before_noon_break_time", fallback="10:00"),
            start_of_day=parser.get("appt", "start_of_day", fallback="9:00"),
            hours_per_day=parser.getint("appt", "hours_per_day", fallback=9),
            def_task_len=parser.getint("tasks", "def_task_len", fallback=6),
            min_task_split=parser.getint("tasks", "min_task_split", fallback=60),
            ilm=parser.get("tags", "ilm", fallback="ilm"),
            tag_order=parser.get("tags", "tag_order", fallback="akquise, legal, mail"),
            tag_projects=parser.get("tags", "tag_projects", fallback=""),
            tags_to_ignore=parser.get(
                "tags", "tags_to_ignore", fallback="2private, 2privat"
            ),
            tag_ignore_appt=parser.get("tags", "tag_ignore_appt", fallback="focus time, no ext.* appt.*, ^blocked$"),
            tags_to_create_appt=parser.get("tags", "tags_to_create_appt", fallback="appt"),
            tags_future=parser.get("tags", "tags_future", fallback="future"),
            tags_to_block_time=parser.get("tags", "tags_to_block_time", fallback="block"),
        )

    def save(self, settings):
        parser = ConfigParser()
        if self.path.exists():
            parser.read(self.path, encoding="utf-8")
        values = {
            "taskserver": {"base_url": settings.task_server_url},
            "appt": {"app": settings.calendar_provider, "days_for_scheduling": str(settings.days_for_scheduling),
                     "min_task_len_4_appt": str(settings.min_task_len_4_appt), "lunch_break": str(settings.lunch_break),
                     "short_break": str(settings.short_break), "short_break_after_ilm": str(int(settings.short_break_after_ilm)),
                     "lunch_break_time": settings.lunch_break_time, "before_noon_break_time": settings.before_noon_break_time,
                     "start_of_day": settings.start_of_day, "hours_per_day": str(settings.hours_per_day)},
            "tasks": {"def_task_len": str(settings.def_task_len), "min_task_split": str(settings.min_task_split)},
            "tags": {"ilm": settings.ilm, "tag_order": settings.tag_order, "tag_projects": settings.tag_projects,
                     "tags_to_ignore": settings.tags_to_ignore,
                     "tag_ignore_appt": settings.tag_ignore_appt, "tags_to_create_appt": settings.tags_to_create_appt,
                     "tags_future": settings.tags_future, "tags_to_block_time": settings.tags_to_block_time},
        }
        for section, entries in values.items():
            if not parser.has_section(section):
                parser.add_section(section)
            for key, value in entries.items():
                parser.set(section, key, value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as stream:
            parser.write(stream)

    def app_settings(self) -> AppSettings:
        """Adapt browser settings, retaining legacy INI values until overridden."""
        settings = self.load()
        parser = ConfigParser()
        legacy = Path(__file__).resolve().parents[1] / "lurchcal.ini"
        parser.read(legacy, encoding="utf-8")
        web = ConfigParser()
        if self.path.exists():
            web.read(self.path, encoding="utf-8")
        defaults = {
            "appt": {"min_task_len_4_appt": str(settings.min_task_len_4_appt), "lunch_break": str(settings.lunch_break),
                     "short_break": str(settings.short_break), "short_break_after_ilm": str(int(settings.short_break_after_ilm)),
                     "days_for_scheduling": str(settings.days_for_scheduling), "lunch_break_time": settings.lunch_break_time,
                     "before_noon_break_time": settings.before_noon_break_time, "start_of_day": settings.start_of_day,
                     "hours_per_day": str(settings.hours_per_day), "app": settings.calendar_provider},
            "tasks": {"def_task_len": str(settings.def_task_len), "min_task_split": str(settings.min_task_split)},
            "tags": {"ilm": settings.ilm, "tag_order": settings.tag_order, "tag_projects": settings.tag_projects,
                     "tags_to_ignore": settings.tags_to_ignore,
                     "tag_ignore_appt": settings.tag_ignore_appt, "tags_to_create_appt": settings.tags_to_create_appt,
                     "tags_future": settings.tags_future, "tags_to_block_time": settings.tags_to_block_time},
            "taskserver": {"base_url": settings.task_server_url},
        }
        for section, entries in defaults.items():
            if not parser.has_section(section):
                parser.add_section(section)
            for key, value in entries.items():
                if not parser.has_option(section, key) or web.has_option(section, key):
                    parser.set(section, key, value)
        return settings_from_config(parser)