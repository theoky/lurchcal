from datetime import datetime, timedelta

from lurchcal.ScheduledTask import ScheduledTask
from lurchcal.Task import Task
from lurchcal.lurchcal_wf import group_default_duration_appointments
from lurchcal.CalendarGoogle import CalendarGoogle
from lurchcal.CalendarOutlook import CalendarOutlook


def scheduled(description, start, duration=6, is_default=True):
    task = Task(description, duration=duration)
    task.is_default_duration = is_default
    return ScheduledTask(start, task, duration)


def test_groups_consecutive_default_duration_tasks_without_mutating_inputs():
    start = datetime(2026, 10, 12, 9)
    first = scheduled("First", start)
    second = scheduled("Second", start + timedelta(minutes=6))
    third = scheduled("Third", start + timedelta(minutes=12))

    result = group_default_duration_appointments([first, second, third], 6)

    assert len(result) == 1
    assert result[0].start == start
    assert result[0].duration == 18
    assert result[0].task.description == "First\nSecond\nThird"
    assert result[0]._grouped_default_tasks == ["First", "Second", "Third"]
    assert first.duration == second.duration == third.duration == 6
    assert first.task.description == "First"


def test_does_not_group_across_gaps_or_with_explicit_or_split_tasks():
    start = datetime(2026, 10, 12, 9)
    tasks = [
        scheduled("Default", start),
        scheduled("Gap", start + timedelta(minutes=7)),
        scheduled("Explicit", start + timedelta(minutes=13), 6, False),
        scheduled("Split", start + timedelta(minutes=19), 6, False),
        scheduled("Next default", start + timedelta(minutes=25)),
    ]

    result = group_default_duration_appointments(tasks, 6)

    assert result == tasks
    assert all(not hasattr(item, "_grouped_default_tasks") for item in result)


def test_does_not_group_tasks_with_different_appointment_metadata():
    start = datetime(2026, 10, 12, 9)
    first = scheduled("First", start)
    second = scheduled("Tagged", start + timedelta(minutes=6))
    second.task.tags = ["appt"]

    result = group_default_duration_appointments([first, second], 6)

    assert len(result) == 2


def test_google_calendar_uses_grouped_title_and_includes_every_task(monkeypatch):
    start = datetime(2026, 10, 12, 9)
    grouped = group_default_duration_appointments(
        [scheduled("First", start), scheduled("Second", start + timedelta(minutes=6))], 6
    )
    batch = type("Batch", (), {"add": lambda self, request: self.requests.append(request),
                               "execute": lambda self: None})()
    batch.requests = []

    class Events:
        def insert(self, **kwargs):
            return kwargs["body"]

    service = type("Service", (), {"new_batch_http_request": lambda self: batch,
                                   "events": lambda self: Events()})()
    monkeypatch.setattr("lurchcal.CalendarGoogle.build", lambda *args, **kwargs: service)
    CalendarGoogle().create_appointments_4_tasks(grouped)

    assert batch.requests[0]["summary"] == "Gruppierte Aufgaben"
    assert "First\nSecond" in batch.requests[0]["description"]
    assert batch.requests[0]["transparency"] == "transparent"
    assert batch.requests[0]["visibility"] == "private"


def test_outlook_calendar_uses_grouped_title_and_body(monkeypatch):
    start = datetime(2026, 10, 12, 9)
    grouped = group_default_duration_appointments(
        [scheduled("First", start), scheduled("Second", start + timedelta(minutes=6))], 6
    )
    appt = type("Appointment", (), {"UserProperties": type("Properties", (), {
        "Add": lambda self, *args: type("Property", (), {})()
    })(), "Save": lambda self: None})()
    items = type("Items", (), {"Add": lambda self: appt})()
    outlook = CalendarOutlook()
    outlook.outlook = type("Outlook", (), {"GetDefaultFolder": lambda self, _: type(
        "Folder", (), {"Items": items}
    )()})()

    outlook.create_appointments_4_tasks(grouped)

    assert appt.Subject == "Gruppierte Aufgaben"
    assert "First\nSecond" in appt.Body
    assert appt.BusyStatus == 0
    assert appt.Sensitivity == 2