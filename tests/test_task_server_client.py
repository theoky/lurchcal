"""Controlled HTTP boundary tests for the LurchCal Task Server client."""
from datetime import date, datetime
from unittest.mock import Mock

import pytest
import requests

from lurchcal.ScheduledTask import ScheduledTask
from lurchcal.Task import Task
from lurchcal.TaskServerClient import (
    InvalidTaskSourceConfiguration,
    SchedulePublicationError,
    TaskServerClient,
    TaskServerUnavailable,
)


def response(status, body):
    result = Mock()
    result.status_code = status
    result.json.return_value = body
    result.text = str(body)
    if status >= 400:
        result.raise_for_status.side_effect = requests.HTTPError(str(body))
    else:
        result.raise_for_status.return_value = None
    return result


def test_get_tasks_uses_explicit_date_and_connect_read_timeouts():
    session = Mock()
    session.request.return_value = response(200, {"tasks": [{"id": "1"}]})
    client = TaskServerClient("http://127.0.0.1:8001/", session=session)
    assert client.get_tasks(date(2026, 10, 4)) == [{"id": "1"}]
    session.request.assert_called_once_with(
        "GET", "http://127.0.0.1:8001/api/v1/tasks",
        timeout=(3.0, 30.0), params={"as_of": "2026-10-04"},
    )


def test_connection_failure_is_mapped_to_application_exception():
    session = Mock()
    session.request.side_effect = requests.ConnectionError("refused")
    client = TaskServerClient(session=session)
    with pytest.raises(TaskServerUnavailable, match="python -m task_server"):
        client.get_tasks(date(2026, 10, 4))


def test_timeout_is_mapped_to_application_exception():
    session = Mock()
    session.request.side_effect = requests.Timeout("late")
    with pytest.raises(TaskServerUnavailable, match="timed out"):
        TaskServerClient(session=session).get_tasks(date.today())


def test_source_configuration_response_is_mapped():
    session = Mock()
    session.request.return_value = response(422, {"detail": "Zim path not configured"})
    with pytest.raises(InvalidTaskSourceConfiguration, match="not configured"):
        TaskServerClient(session=session).get_tasks(date.today())


def test_publication_serializes_scheduled_tasks_and_maps_failure():
    task = Task("Write report", prio=2, source_name="Work")
    task.tags = ["work"]
    scheduled = [ScheduledTask(datetime(2026, 10, 5, 9), task, 30)]
    session = Mock()
    session.request.return_value = response(200, {"published": True, "task_count": 1, "path": "server"})
    client = TaskServerClient(session=session)
    assert client.publish_schedule(scheduled)["published"] is True
    payload = session.request.call_args.kwargs["json"]
    assert payload == {"scheduled_tasks": [{
        "start": "2026-10-05T09:00:00", "duration": 30, "priority": 2,
        "description": "Write report", "tags": ["work"], "source_name": "Work",
    }]}

    session.request.return_value = response(503, {"detail": "Output unavailable"})
    with pytest.raises(SchedulePublicationError, match="Output unavailable"):
        client.publish_schedule(scheduled)


def test_publication_network_error_is_publication_error():
    session = Mock()
    session.request.side_effect = requests.ConnectionError("offline")
    with pytest.raises(SchedulePublicationError):
        TaskServerClient(session=session).publish_schedule([])