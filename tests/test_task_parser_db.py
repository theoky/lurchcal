"""Unit tests for TaskParser using deterministic Zim fixtures."""

import pytest
from kivy.config import ConfigParser

from lurchcal.TaskParser import TaskParser


@pytest.fixture()
def parser_config():
    config = ConfigParser()
    config.add_section("tasks")
    config.set("tasks", "def_task_len", "30")
    config.set("tasks", "min_task_split", "60")
    return config


@pytest.fixture()
def parser(parser_config):
    return TaskParser(parser_config)


def test_parse_zim_tasks_splits_and_filters(parser, db_path):
    tasks = parser.parse_zim_tasks(str(db_path))
    descriptions = [task.description for task in tasks]

    assert descriptions == [
        "Write summary",
        "st: Long Focus Task ~2h~ @Deep",
        "Long Focus Task ~2h~ @Deep",
    ]
    assert [task.duration for task in tasks] == [30, 60, 60]
    assert [task.subid for task in tasks] == [0, 1, 0]

    for task in tasks:
        assert task.source_name == "Work"
        assert "Waiting Task" not in task.description

    deep_tags = [task.tags for task in tasks[1:]]
    assert all(tag_list == ["deep"] for tag_list in deep_tags)


def test_parse_task_description_from_fixture(parser):
    description = "Long Focus Task ~2h~a @Deep"
    duration, is_default, assign_duration, tags = parser.parse_task_description(description)

    assert duration == 120
    assert not is_default
    assert assign_duration
    assert tags == ["deep"]
