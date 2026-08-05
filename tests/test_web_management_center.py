

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

from __future__ import annotations

from fastapi.testclient import TestClient
from cli.web_app import create_app

def test_api_cliproxy_status_offline(monkeypatch):
    import socket

    def blocked(*_a, **_k):
        raise OSError("network blocked by test")

    monkeypatch.setattr(socket, "create_connection", blocked)

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/cliproxy/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["reachable"] is False
    assert "configured_base_url" in data
    
    # Ensure no secrets leak
    assert not any(k.endswith("key") or "secret" in k.lower() for k in data.keys())
    assert data["configured_base_url"] == "http://127.0.0.1:8317/v1"


from typing import Any, Dict
from fastapi.testclient import TestClient
import pytest
from cli.web_app import create_app
from core.history import TaskHistory

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_api_spend_empty(monkeypatch, client):
    # Mock history list to return empty
    monkeypatch.setattr(TaskHistory, "list", lambda self, limit=20: [])
    
    response = client.get("/api/spend")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    # Check zeroed values
    assert data["estimated_cost_usd"] == 0.0
    assert data["tokens"] == 0
    assert "by_model" in data
    assert data["by_model"] == {}
    
    # Preserve estimate_source fidelity even in empty case
    assert "estimate_source" in data

def test_api_spend_populated(monkeypatch, client):
    mock_history = [
        {"model": "gpt-4", "estimated_cost_usd": 0.05, "tokens": 1000, "cost_source": "usage", "estimate_source": "registry"},
        {"model": "claude", "estimated_cost_usd": 0.02, "tokens": 500, "cost_source": "estimate", "estimate_source": "fallback"},
    ]
    monkeypatch.setattr(TaskHistory, "list", lambda self, limit=20: mock_history)
    
    response = client.get("/api/spend")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    
    assert data["estimated_cost_usd"] == 0.07
    assert data["tokens"] == 1500
    assert data["estimate_source"] == "fallback" # fallback overrides registry
    
    assert "by_model" in data
    assert "gpt-4" in data["by_model"]
    assert "claude" in data["by_model"]
    
    assert data["by_model"]["gpt-4"]["estimated_cost_usd"] == 0.05
    assert data["by_model"]["gpt-4"]["estimate_source"] == "registry"
    
    assert data["by_model"]["claude"]["estimated_cost_usd"] == 0.02
    assert data["by_model"]["claude"]["estimate_source"] == "fallback"

