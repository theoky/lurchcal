"""Scheduling service boundary tests without a running calendar provider."""
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


def test_scheduling_service_retrieves_dtos_and_publishes_schedule(monkeypatch):
    dto = {
        "id": "task-1", "parent_id": None, "description": "Work ~30m~ @focus",
        "priority": 1, "start_date": "2000-01-01", "due_date": "2026-10-05",
        "source_name": "Work", "has_children": False,
    }
    service = Mock()
    service.get_tasks.return_value = [dto]
    service.publish_schedule.return_value = {"published": True}
    monkeypatch.setattr(lurchcal_wf, "TaskServerClient", lambda _: service)
    monkeypatch.setattr(lurchcal_wf.SchedulingService, "__init__", lambda self, settings, **kwargs: _service_init(
        self, settings, service))

    calendar = Mock()
    calendar.get_appointments.return_value = []
    monkeypatch.setattr(lurchcal_wf.CalendarFactory, "create_calendar", lambda _: calendar)
    scheduled = [ScheduledTask(datetime(2026, 10, 5, 9), Task("Work", prio=1), 30)]
    unscheduled = [Task("Leftover")]
    scheduler = Mock()
    scheduler.schedule_everything.return_value = (scheduled, unscheduled)
    monkeypatch.setattr(lurchcal_wf, "TaskScheduler", lambda _: scheduler)

    events = []
    result = lurchcal_wf.SchedulingService(settings()).create_schedule(progress=events.append)
    assert result.unscheduled_tasks == unscheduled
    service.get_tasks.assert_called_once_with(date.today())
    service.publish_schedule.assert_called_once_with(scheduled)
    assert [event["stage"] for event in events][-1] == "complete"


def test_scheduling_service_surfaces_server_failure_before_calendar_creation(monkeypatch):
    client = Mock()
    client.get_tasks.side_effect = TaskServerUnavailable("Task Server offline")
    monkeypatch.setattr(lurchcal_wf, "TaskServerClient", lambda _: client)
    monkeypatch.setattr(lurchcal_wf.SchedulingService, "__init__", lambda self, settings, **kwargs: _service_init(
        self, settings, client))
    calendar_factory = Mock()
    monkeypatch.setattr(lurchcal_wf, "CalendarFactory", calendar_factory)
    try:
        lurchcal_wf.SchedulingService(settings()).create_schedule()
    except TaskServerUnavailable as exc:
        assert "offline" in str(exc)
    else:
        raise AssertionError("Task Server failure should be propagated as a clear app error")
    calendar_factory.create_calendar.assert_not_called()


def test_scheduling_service_is_ui_independent_and_returns_structured_result(monkeypatch):
    dto = {
        "id": "task-1", "parent_id": None, "description": "Work ~30m~ @focus",
        "priority": 1, "start_date": "2000-01-01", "due_date": "2026-10-05",
        "source_name": "Work", "has_children": False,
    }
    server = Mock()
    server.get_tasks.return_value = [dto]
    server.publish_schedule.return_value = {"published": True}
    monkeypatch.setattr(lurchcal_wf, "TaskServerClient", lambda _: server)
    monkeypatch.setattr(lurchcal_wf.SchedulingService, "__init__", lambda self, settings, **kwargs: _service_init(
        self, settings, server))
    calendar = Mock()
    calendar.get_appointments.return_value = []
    monkeypatch.setattr(lurchcal_wf.CalendarFactory, "create_calendar", lambda _: calendar)
    scheduled = [ScheduledTask(datetime(2026, 10, 5, 9), Task("Work", prio=1), 30)]
    unscheduled = [Task("Leftover")]
    scheduler = Mock()
    scheduler.schedule_everything.return_value = (scheduled, unscheduled)
    monkeypatch.setattr(lurchcal_wf, "TaskScheduler", lambda _: scheduler)
    events = []
    result = lurchcal_wf.SchedulingService(settings()).create_schedule(progress=events.append)
    assert result.scheduled_tasks == scheduled
    assert result.unscheduled_tasks == unscheduled
    assert result.statistics["scheduled_count"] == 1
    assert events[-1]["stage"] == "complete"


def test_remove_appointments_action_remains_calendar_only(monkeypatch):
    calendar = Mock()
    service = lurchcal_wf.SchedulingService(
        settings(), calendar_factory=Mock(create_calendar=lambda _: calendar)
    )
    events = []
    service.remove_calendar_appointments(progress=events.append)
    calendar.authenticate.assert_called_once_with()
    calendar.delete_lurchcal_meetings.assert_called_once()
    assert events[-1]["stage"] == "complete"


def _service_init(instance, settings_value, task_client):
    instance.settings = settings_value
    instance.calendar_factory = lurchcal_wf.CalendarFactory
    instance.task_client_factory = lambda _: task_client


def test_build_tree_handles_numeric_and_string_parent_ids():
    parent = Task("Parent", id="1", parent=0, has_children=True)
    child = Task("Child", id="2", parent="1")

    tree = lurchcal_wf.build_tree([child, parent])

    assert tree.children[0].get_attr("task") is parent
    assert tree.children[0].children[0].get_attr("task") is child