import subprocess
import sys
from pathlib import Path


def test_domain_workflow_and_adapters_import_without_kivy():
    modules = [
        "lurchcal.Task", "lurchcal.TaskParser", "lurchcal.TaskScheduler",
        "lurchcal.Day", "lurchcal.ScheduledTask", "lurchcal.task_tools",
        "lurchcal.lurchcal_wf", "lurchcal.CalendarOutlook", "lurchcal.CalendarGoogle",
    ]
    code = (
        "import importlib, sys; "
        f"[importlib.import_module(name) for name in {modules!r}]; "
        "assert not any(name == 'kivy' or name.startswith('kivy.') for name in sys.modules)"
    )
    source = str(Path(__file__).resolve().parents[1] / "src")
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True,
        env={**__import__("os").environ, "PYTHONPATH": source},
    )
    assert result.returncode == 0, result.stderr