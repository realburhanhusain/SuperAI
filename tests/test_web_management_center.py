"""Tests for web management center API endpoints."""

import os
from pathlib import Path
import pytest

pytestmark = pytest.mark.unit

def test_api_goals_not_running(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    # Reload to pick up new home
    import importlib
    import core.goals_daemon as gd
    importlib.reload(gd)

    from cli.web_app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())

    r = client.get("/api/goals")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["running"] is False
    assert body["pid"] is None


def test_api_goals_running(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    import importlib
    import core.goals_daemon as gd
    importlib.reload(gd)

    # Fake a running daemon
    pid = os.getpid()
    gd.write_pid(pid)
    gd.save_state({"interval_sec": 30.0, "ticks_total": 42})

    from cli.web_app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())

    r = client.get("/api/goals")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["running"] is True
    assert body["pid"] == pid
    assert body["config"]["interval_sec"] == 30.0
    assert body["ticks_total"] == 42
