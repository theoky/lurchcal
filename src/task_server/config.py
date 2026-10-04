"""Local INI persistence for Task Server source settings."""
from configparser import ConfigParser
import os
from pathlib import Path

from .models import TaskServerSettings


def default_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "LurchCal" / "task_server.ini"


class SettingsStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.environ.get("LURCHCAL_TASK_SERVER_CONFIG", default_config_path()))

    def load(self) -> TaskServerSettings:
        parser = ConfigParser()
        if self.path.exists():
            parser.read(self.path, encoding="utf-8")
        return TaskServerSettings(
            path_db=parser.get("zim", "path_db", fallback=""),
            path_page=parser.get("zim", "path_page", fallback=""),
        )

    def save(self, settings: TaskServerSettings) -> None:
        parser = ConfigParser()
        parser["zim"] = {"path_db": settings.path_db, "path_page": settings.path_page}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as stream:
            parser.write(stream)