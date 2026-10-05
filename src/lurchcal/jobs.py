"""Small in-memory background job registry for the single-user local server."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4


def _serialize(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if is_dataclass(value):
        return _serialize(asdict(value))
    if hasattr(value, "task"):
        return {"start": _serialize(value.start), "duration": value.duration,
                "description": value.task.description, "priority": value.task.prio,
                "tags": list(value.task.tags), "source_name": value.task.source_name}
    if hasattr(value, "start") and hasattr(value, "duration"):
        return {"start": _serialize(value.start), "duration": value.duration,
                "description": getattr(value.task, "description", str(value))}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "description"):
        return {"description": value.description}
    return str(value)


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "queued"
    progress: list[dict] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self):
        return {"id": self.id, "status": self.status, "progress": list(self.progress),
                "result": self.result, "error": self.error,
                "created_at": self.created_at, "updated_at": self.updated_at}


class JobManager:
    def __init__(self, max_workers=1, executor=None):
        self._lock = Lock()
        self._jobs = {}
        self._executor = executor or ThreadPoolExecutor(max_workers=max_workers,
                                                        thread_name_prefix="lurchcal-worker")

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def submit(self, operation):
        job = Job()
        with self._lock:
            self._jobs[job.id] = job
        self._executor.submit(self._run, job.id, operation)
        return job

    def run_in_worker(self, operation):
        """Synchronously return a value while executing provider access in worker thread."""
        return self._executor.submit(self._execute_in_worker, operation).result()

    @staticmethod
    def _execute_in_worker(operation):
        import sys
        pythoncom = None
        if sys.platform == "win32":
            try:
                import pythoncom as _pythoncom
                pythoncom = _pythoncom
                pythoncom.CoInitialize()
            except ImportError:
                pythoncom = None
        try:
            return operation()
        finally:
            if pythoncom is not None:
                pythoncom.CoUninitialize()

    def _run(self, job_id, operation):
        job = self.get(job_id)
        with self._lock:
            job.status = "running"
            job.updated_at = datetime.now(timezone.utc).isoformat()
        def progress(event):
            with self._lock:
                job.progress.append(_serialize(event))
                job.updated_at = datetime.now(timezone.utc).isoformat()
        try:
            result = self._execute_in_worker(lambda: operation(progress))
            with self._lock:
                job.result = _serialize(result)
                job.status = "succeeded"
        except Exception as exc:
            with self._lock:
                job.error = str(exc)
                job.status = "failed"
        finally:
            with self._lock:
                job.updated_at = datetime.now(timezone.utc).isoformat()