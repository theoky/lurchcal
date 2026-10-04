from datetime import time
from configparser import ConfigParser

from lurchcal.settings import settings_from_config


def test_ini_config_adapts_tag_lists_and_times():
    config = ConfigParser()
    config.read_dict({
        "appt": {"min_task_len_4_appt": "15", "lunch_break": "30", "short_break": "15",
                 "short_break_after_ilm": "1", "days_for_scheduling": "7", "lunch_break_time": "12:00",
                 "before_noon_break_time": "10:00", "start_of_day": "08:30", "hours_per_day": "9", "app": "OUTLOOK"},
        "tasks": {"def_task_len": "6", "min_task_split": "60"},
        "tags": {"ilm": "ilm", "tag_order": "akquise, legal", "tag_projects": "", "tag_ignore_appt": "focus time, ^blocked$",
                 "tags_to_create_appt": "appt", "tags_future": "future", "tags_to_block_time": "block"},
        "taskserver": {"base_url": "http://127.0.0.1:8001"},
    })
    settings = settings_from_config(config)
    assert settings.appt.start_of_day == time(8, 30)
    assert settings.appt.app == "outlook"
    assert settings.tags.tag_order == ("akquise", "legal")
    assert settings.tags.tag_ignore_appt == ("focus time", "^blocked$")
    assert settings.task_server_url == "http://127.0.0.1:8001"


def test_task_server_base_url_defaults_without_zim_paths():
    config = ConfigParser()
    config.read_dict({
        "appt": {"min_task_len_4_appt": "15", "lunch_break": "30", "short_break": "15",
                 "short_break_after_ilm": "1", "days_for_scheduling": "7", "lunch_break_time": "12:00",
                 "before_noon_break_time": "10:00", "start_of_day": "08:30", "hours_per_day": "9", "app": "OUTLOOK"},
        "tasks": {"def_task_len": "6", "min_task_split": "60"},
        "tags": {"ilm": "ilm", "tag_order": "", "tag_projects": "", "tag_ignore_appt": "",
                 "tags_to_create_appt": "", "tags_future": "", "tags_to_block_time": ""},
    })
    settings = settings_from_config(config)
    assert settings.task_server_url == "http://127.0.0.1:8001"
    assert not hasattr(settings, "zim")


def test_task_server_base_url_reads_legacy_underscore_section():
    config = ConfigParser()
    config.read_dict({
        "appt": {"min_task_len_4_appt": "15", "lunch_break": "30", "short_break": "15",
                 "short_break_after_ilm": "1", "days_for_scheduling": "7", "lunch_break_time": "12:00",
                 "before_noon_break_time": "10:00", "start_of_day": "08:30", "hours_per_day": "9", "app": "OUTLOOK"},
        "tasks": {"def_task_len": "6", "min_task_split": "60"},
        "tags": {"ilm": "ilm", "tag_order": "", "tag_projects": "", "tag_ignore_appt": "",
                 "tags_to_create_appt": "", "tags_future": "", "tags_to_block_time": ""},
        "task_server": {"base_url": "http://127.0.0.1:8002"},
    })
    assert settings_from_config(config).task_server_url == "http://127.0.0.1:8002"


def test_legacy_zim_settings_migrate_once_to_task_server_ini(tmp_path):
    from lurchcal.settings import migrate_legacy_zim_settings

    legacy = tmp_path / "lurchal.ini"
    legacy.write_text("[zim]\npath_db = C:/wiki/index.db\npath_page = C:/wiki/tasks.txt\n", encoding="utf-8")
    target = tmp_path / "task_server.ini"
    assert migrate_legacy_zim_settings(str(legacy), str(target)) is True
    assert migrate_legacy_zim_settings(str(legacy), str(target)) is False
    migrated = ConfigParser()
    migrated.read(target, encoding="utf-8")
    assert migrated.get("zim", "path_db") == "C:/wiki/index.db"
    assert migrated.get("zim", "path_page") == "C:/wiki/tasks.txt"


def test_existing_task_server_settings_are_not_overwritten_by_legacy_migration(tmp_path):
    from lurchcal.settings import migrate_legacy_zim_settings

    legacy = tmp_path / "lurchal.ini"
    legacy.write_text("[zim]\npath_db = old.db\npath_page = old.txt\n", encoding="utf-8")
    target = tmp_path / "task_server.ini"
    target.write_text("[zim]\npath_db = new.db\npath_page = new.txt\n", encoding="utf-8")
    assert migrate_legacy_zim_settings(str(legacy), str(target)) is False
    migrated = ConfigParser()
    migrated.read(target, encoding="utf-8")
    assert migrated.get("zim", "path_db") == "new.db"


def test_legacy_zim_migration_skips_missing_source_path(tmp_path):
    from lurchcal.settings import migrate_legacy_zim_settings

    assert migrate_legacy_zim_settings(None, str(tmp_path / "task_server.ini")) is False
    assert not (tmp_path / "task_server.ini").exists()