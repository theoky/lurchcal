"""HTTP boundary to the independent local Task Server."""
from datetime import date, datetime
import logging

import requests

logger = logging.getLogger(__name__)


class TaskServerError(RuntimeError):
    """Base application-level error for Task Server operations."""


class TaskServerUnavailable(TaskServerError):
    """The Task Server could not be reached or failed unexpectedly."""


class InvalidTaskSourceConfiguration(TaskServerError):
    """The Task Server has missing or invalid source configuration."""


class SchedulePublicationError(TaskServerError):
    """The Task Server could not publish the generated schedule."""


class TaskServerClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        *,
        connect_timeout: float = 3.0,
        read_timeout: float = 30.0,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = (connect_timeout, read_timeout)
        self.session = session or requests.Session()

    def _request(self, method: str, endpoint: str, *, operation: str, **kwargs):
        try:
            response = self.session.request(
                method, f"{self.base_url}{endpoint}", timeout=self.timeout, **kwargs
            )
        except requests.Timeout as exc:
            logger.warning("Task Server %s request timed out", operation)
            error_type = SchedulePublicationError if operation == "schedule publication" else TaskServerUnavailable
            raise error_type(
                f"Task Server timed out during {operation}. Confirm it is running at {self.base_url}."
            ) from exc
        except requests.ConnectionError as exc:
            logger.warning("Task Server is unreachable during %s", operation)
            message = f"Task Server is unavailable at {self.base_url}. Start it with `python -m task_server`."
            error_type = SchedulePublicationError if operation == "schedule publication" else TaskServerUnavailable
            raise error_type(message) from exc
        except requests.RequestException as exc:
            logger.exception("Task Server HTTP request failed during %s", operation)
            raise TaskServerUnavailable(f"Task Server request failed during {operation}: {exc}") from exc

        if response.status_code == 422 and operation == "task retrieval":
            detail = self._response_detail(response)
            raise InvalidTaskSourceConfiguration(detail)
        if response.status_code == 422:
            raise SchedulePublicationError(self._response_detail(response))
        if response.status_code >= 500:
            detail = self._response_detail(response)
            if operation == "schedule publication":
                raise SchedulePublicationError(detail)
            raise TaskServerUnavailable(detail)
        try:
            response.raise_for_status()
            return response.json()
        except (requests.HTTPError, ValueError) as exc:
            detail = self._response_detail(response)
            if operation == "schedule publication":
                raise SchedulePublicationError(detail) from exc
            raise TaskServerUnavailable(detail) from exc

    @staticmethod
    def _response_detail(response: requests.Response) -> str:
        try:
            body = response.json()
            detail = body.get("detail", body)
            return str(detail)
        except ValueError:
            return response.text or f"HTTP {response.status_code}"

    def health(self) -> dict:
        return self._request("GET", "/api/v1/health", operation="health check")

    def capabilities(self) -> dict:
        return self._request("GET", "/api/v1/capabilities", operation="capability check")

    def get_tasks(self, as_of: date) -> list[dict]:
        result = self._request(
            "GET", "/api/v1/tasks", operation="task retrieval",
            params={"as_of": as_of.isoformat()},
        )
        return result["tasks"]

    def publish_schedule(self, scheduled_tasks) -> dict:
        items = [
            {
                "start": item.start.isoformat() if isinstance(item.start, datetime) else item.start,
                "duration": item.duration,
                "priority": item.task.prio,
                "description": item.task.description,
                "tags": list(item.task.tags),
                "source_name": item.task.source_name,
            }
            for item in scheduled_tasks
        ]
        return self._request(
            "POST", "/api/v1/schedule-publications", operation="schedule publication",
            json={"scheduled_tasks": items},
        )