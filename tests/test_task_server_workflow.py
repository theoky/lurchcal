"""Kivy workflow boundary tests without requiring a running calendar provider."""
from datetime import date, datetime, time
from unittest.mock import Mock

from lurchcal.settings import AppSettings, AppointmentSettings, TagSettings, TaskSettings
from lurchcal.Task import Task
from lurchcal.ScheduledTask import ScheduledTask
from lurchcal.TaskServerClient import TaskServerUnavailable
from lurchcal import lurchcal_wf


def settings():
    return AppSettings(
        appt=AppointmentSettings(15, 30, 15, 1, 7, time(12), time(10), time(9), 8, "outlook"),
        tasks=TaskSettings(6, 60),
        tags=TagSettings("ilm", (), (), (), ("appt",), ("future",), ("block",)),
    )


def test_kivy_workflow_retrieves_dtos_and_publishes_schedule(monkeypatch):
    dto = {
        "id": "task-1", "parent_id": None, "description": "Work ~30m~ @focus",
        "priority": 1, "start_date": "2000-01-01", "due_date": "2026-10-05",
        "source_name": "Work", "has_children": False,
    }
    service = Mock()
    service.get_tasks.return_value = [dto]
    service.publish_schedule.return_value = {"published": True}
    monkeypatch.setattr(lurchcal_wf, "TaskServerClient", lambda _: service)

    calendar = Mock()
    calendar.get_appointments.return_value = []
    monkeypatch.setattr(lurchcal_wf.CalendarFactory, "create_calendar", lambda _: calendar)
    scheduled = [ScheduledTask(datetime(2026, 10, 5, 9), Task("Work", prio=1), 30)]
    unscheduled = [Task("Leftover")]
    scheduler = Mock()
    scheduler.schedule_everything.return_value = (scheduled, unscheduled)
    monkeypatch.setattr(lurchcal_wf, "TaskScheduler", lambda _: scheduler)

    ticks = []
    actual = lurchcal_wf.create_task_appointments(lambda: ticks.append(1), False, settings())
    assert actual == unscheduled
    service.get_tasks.assert_called_once_with(date.today())
    service.publish_schedule.assert_called_once_with(scheduled)
    assert len(ticks) == 6


def test_kivy_workflow_surfaces_server_failure_before_calendar_creation(monkeypatch):
    client = Mock()
    client.get_tasks.side_effect = TaskServerUnavailable("Task Server offline")
    monkeypatch.setattr(lurchcal_wf, "TaskServerClient", lambda _: client)
    calendar_factory = Mock()
    monkeypatch.setattr(lurchcal_wf, "CalendarFactory", calendar_factory)
    try:
        lurchcal_wf.create_task_appointments(lambda: None, False, settings())
    except TaskServerUnavailable as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("Task Server failure should be propagated as a clear app error")
    calendar_factory.create_calendar.assert_not_called()


def test_remove_appointments_action_remains_calendar_only(monkeypatch):
    calendar = Mock()
    monkeypatch.setattr(lurchcal_wf.CalendarFactory, "create_calendar", lambda _: calendar)
    ticks = []
    lurchcal_wf.remove_appointments(lambda: ticks.append(1), None, settings())
    calendar.authenticate.assert_called_once_with()
    calendar.delete_lurchcal_meetings.assert_called_once()
    assert ticks == [1]


def test_build_tree_handles_numeric_and_string_parent_ids():
    parent = Task("Parent", id="1", parent=0, has_children=True)
    child = Task("Child", id="2", parent="1")

    tree = lurchcal_wf.build_tree([child, parent])

    assert tree.children[0].get_attr("task") is parent
    assert tree.children[0].children[0].get_attr("task") is child