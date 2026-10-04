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
        "zim": {"path_db": "db", "path_page": "page"},
    })
    settings = settings_from_config(config)
    assert settings.appt.start_of_day == time(8, 30)
    assert settings.appt.app == "outlook"
    assert settings.tags.tag_order == ("akquise", "legal")
    assert settings.tags.tag_ignore_appt == ("focus time", "^blocked$")