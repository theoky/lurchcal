import importlib


def test_web_server_defaults_to_loopback_and_configurable_port(monkeypatch):
    module = importlib.import_module("lurchcal.web_server")
    calls = []
    monkeypatch.setattr(module.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.delenv("LURCHCAL_WEB_HOST", raising=False)
    monkeypatch.delenv("LURCHCAL_WEB_PORT", raising=False)

    module.main()

    assert calls[-1][1]["host"] == "127.0.0.1"
    assert calls[-1][1]["port"] == 8000
    monkeypatch.setenv("LURCHCAL_WEB_HOST", "127.0.0.1")
    monkeypatch.setenv("LURCHCAL_WEB_PORT", "8123")
    module.main()
    assert calls[-1][1]["port"] == 8123


def test_task_server_defaults_to_loopback_and_configurable_port(monkeypatch):
    module = importlib.import_module("task_server.__main__")
    calls = []
    monkeypatch.setattr(module.uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.delenv("LURCHCAL_TASK_SERVER_HOST", raising=False)
    monkeypatch.delenv("LURCHCAL_TASK_SERVER_PORT", raising=False)

    module.main()

    assert calls[-1][1]["host"] == "127.0.0.1"
    assert calls[-1][1]["port"] == 8001
    monkeypatch.setenv("LURCHCAL_TASK_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("LURCHCAL_TASK_SERVER_PORT", "8124")
    module.main()
    assert calls[-1][1]["port"] == 8124