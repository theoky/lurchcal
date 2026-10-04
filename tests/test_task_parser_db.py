"""Unit tests for TaskParser using deterministic Zim fixtures."""

import pytest
from datetime import time
from lurchcal.TaskParser import TaskParser
from lurchcal.settings import AppSettings, AppointmentSettings, TaskSettings, TagSettings
from lurchcal.lurchcal_wf import build_tree
from bigtree import preorder_iter
from lurchcal.Task import Task


@pytest.fixture()
def parser_config():
    return AppSettings(
        appt=AppointmentSettings(15, 30, 15, 1, 7, time(12), time(10), time(9), 8, 'outlook'),
        tasks=TaskSettings(30, 60),
        tags=TagSettings('ilm', ('priority1', 'priority2'), (), ('ignore_me',), ('appt',), ('future',), ('block',)),
    )


@pytest.fixture()
def parser(parser_config):
    return TaskParser(parser_config)


def test_parse_source_neutral_tasks_splits_and_filters(parser):
    tasks = parser.parse_tasks([
        {"id": "1", "parent_id": None, "description": "Long Focus Task ~2h~ @Deep",
         "priority": 3, "start_date": "2000-01-01", "due_date": "2024-01-02",
         "source_name": "Work", "has_children": False},
        {"id": "2", "parent_id": None, "description": "Write summary",
         "priority": 1, "start_date": "2000-01-01", "due_date": "2024-01-01",
         "source_name": "Work", "has_children": False},
    ])
    descriptions = [task.description for task in tasks]

    assert descriptions == [
        "st: Long Focus Task ~2h~ @Deep",
        "Long Focus Task ~2h~ @Deep",
        "Write summary",
    ]
    assert [task.duration for task in tasks] == [60, 60, 30]
    assert [task.subid for task in tasks] == [1, 0, 0]

    for task in tasks:
        assert task.source_name == "Work"
        assert "Waiting Task" not in task.description

    assert tasks[0].tags == ["deep"]
    assert tasks[1].tags == ["deep"]
    assert tasks[2].tags == []


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
