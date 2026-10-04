"""Typed INI persistence for settings owned by the LurchCal web service."""
from configparser import ConfigParser
import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from lurchcal.settings import AppSettings, settings_from_config


class LurchCalSettings(BaseModel):
    task_server_url: str = "http://127.0.0.1:8001"
    calendar_provider: str = "outlook"
    days_for_scheduling: int = Field(default=14, ge=1, le=90)

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
            days_for_scheduling=parser.getint("appt", "days_for_scheduling", fallback=14),
        )

    def save(self, settings):
        parser = ConfigParser()
        if self.path.exists():
            parser.read(self.path, encoding="utf-8")
        values = {"taskserver": {"base_url": settings.task_server_url},
                  "appt": {"app": settings.calendar_provider,
                           "days_for_scheduling": str(settings.days_for_scheduling)}}
        for section, entries in values.items():
            if not parser.has_section(section):
                parser.add_section(section)
            for key, value in entries.items():
                parser.set(section, key, value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as stream:
            parser.write(stream)

    def app_settings(self):
        """Adapt persisted web-owned values alongside legacy scheduling defaults."""
        parser = ConfigParser()
        legacy = Path(__file__).resolve().parents[1] / "lurchcal.ini"
        parser.read(legacy, encoding="utf-8")
        settings = settings_from_config(parser)
        web = self.load()
        from dataclasses import replace
        return replace(settings, task_server_url=web.task_server_url,
                       appt=replace(settings.appt, app=web.calendar_provider,
                                    days_for_scheduling=web.days_for_scheduling))