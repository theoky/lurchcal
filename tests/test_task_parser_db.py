"""Unit tests for TaskParser using deterministic Zim fixtures."""

import pytest
from datetime import time
from lurchcal.TaskParser import TaskParser
from lurchcal.settings import AppSettings, AppointmentSettings, TaskSettings, TagSettings, ZimSettings
from lurchcal.lurchcal_wf import build_tree, write_to_zim_page
from bigtree import preorder_iter
from lurchcal.ScheduledTask import ScheduledTask
from lurchcal.Task import Task
from datetime import datetime


@pytest.fixture()
def parser_config():
    return AppSettings(
        appt=AppointmentSettings(15, 30, 15, 1, 7, time(12), time(10), time(9), 8, 'outlook'),
        tasks=TaskSettings(30, 60),
        tags=TagSettings('ilm', ('priority1', 'priority2'), (), ('ignore_me',), ('appt',), ('future',), ('block',)),
        zim=ZimSettings('', ''),
    )


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


def test_parent_child_inherit_tags_and_duration(parser):
    parent = Task("Project ~2h~ @Work", id=10, has_children=True)
    child = Task("Child", id=11, parent=10, has_children=False)
    tree = build_tree([parent, child])
    nodes = list(preorder_iter(tree, filter_condition=lambda node: node.node_name != "0.0"))
    inherited = nodes[1].get_attr("task")
    assert inherited.duration == 121
    assert inherited.tags == ["work"]


def test_schedule_page_keeps_zim_text_format(tmp_path):
    path = tmp_path / "schedule.txt"
    task = Task("Write report", prio=2, source_name="Work")
    task.tags = ["work", "deep"]
    write_to_zim_page(str(path), [ScheduledTask(datetime(2024, 1, 2, 9), task, 30)])
    text = path.read_text(encoding="utf-8")
    assert text.startswith("Content-Type: text/x-zim-wiki\nWiki-Format: zim 0.6\n")
    assert "====== Geplante Tasks ======" in text
    assert "===== 2024-01-02 =====" in text
    assert "* 2024-01-02 09:00:00, 30m, (2): Write report (work, deep), [[Work]]" in text
