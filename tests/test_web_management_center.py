from __future__ import annotations

"""Tests for web management center API endpoints, reverse proxy gateway, and auto-sync engine."""

import os
from pathlib import Path
from typing import Any, Dict
from unittest import mock
import pytest

pytestmark = pytest.mark.unit


def test_api_goals_not_running(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    import importlib
    import core.goals_daemon as gd
    importlib.reload(gd)

    from scli.web_app import create_app
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

    pid = os.getpid()
    gd.write_pid(pid)
    gd.save_state({"interval_sec": 30.0, "ticks_total": 42})

    from scli.web_app import create_app
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


def test_api_cliproxy_status_offline(monkeypatch):
    import socket

    def blocked(*_a, **_k):
        raise OSError("network blocked by test")

    monkeypatch.setattr(socket, "create_connection", blocked)

    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/cliproxy/status")
    assert response.status_code == 200
    data = response.json()
    assert data["reachable"] is False
    assert "configured_base_url" in data
    assert not any(k.endswith("key") or "secret" in k.lower() for k in data.keys())
    assert data["configured_base_url"] == "http://127.0.0.1:8317/v1"


def test_api_spend_empty(monkeypatch):
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    from core.history import TaskHistory

    monkeypatch.setattr(TaskHistory, "list", lambda self, limit=20: [])

    client = TestClient(create_app())
    response = client.get("/api/spend")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["estimated_cost_usd"] == 0.0
    assert data["tokens"] == 0
    assert data["by_model"] == {}
    assert "estimate_source" in data


def test_api_spend_populated(monkeypatch):
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    from core.history import TaskHistory

    mock_history = [
        {"model": "gpt-4", "estimated_cost_usd": 0.05, "tokens": 1000, "cost_source": "usage", "estimate_source": "registry"},
        {"model": "claude", "estimated_cost_usd": 0.02, "tokens": 500, "cost_source": "estimate", "estimate_source": "fallback"},
    ]
    monkeypatch.setattr(TaskHistory, "list", lambda self, limit=20: mock_history)

    client = TestClient(create_app())
    response = client.get("/api/spend")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["estimated_cost_usd"] == 0.07
    assert data["tokens"] == 1500
    assert data["estimate_source"] == "fallback"
    assert "gpt-4" in data["by_model"]
    assert "claude" in data["by_model"]


def test_flag_on_token_unset_route_absent_and_logs(caplog):
    from scli.web_app import create_app

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1"}, clear=True):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/config" not in routes
        assert "SUPERAI_WEB_ENABLE_CONFIG_WRITE is on but SUPERAI_WEB_MANAGEMENT_TOKEN is unset" in caplog.text


def test_flag_on_token_set_request_without_token_on_loopback_refused():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", json={"some": "data"})
        assert response.status_code == 401
        assert "Management token required" in response.json().get("detail", "")


def test_wrong_token_refused():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer badtoken"}, json={"some": "data"})
        assert response.status_code == 401
        assert "Unauthorized management token" in response.json().get("detail", "")


def test_correct_token_accepted():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer secret"}, json={"some": "data"})
        assert response.status_code == 200


def test_superai_web_token_does_not_grant_write_access():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret", "SUPERAI_WEB_TOKEN": "regular"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer regular"}, json={"some": "data"})
        assert response.status_code == 401


def test_console_page_consolidated():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)
    r = client.get("/console")
    assert r.status_code == 200
    assert "SuperAI" in r.text
    assert "Management Center" in r.text


def test_api_audit_missing_token_refused():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit")
        assert response.status_code == 401


def test_api_audit_missing_file_returns_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit", headers={"Authorization": "Bearer secret"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["entries"] == []


def test_api_audit_returns_entries_newest_first(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    from core.audit_log import AuditLog

    audit = AuditLog()
    audit.record("action1", detail={"k": "v1"})
    audit.record("action2", detail={"k": "v2"})
    audit.record("action3", detail={"k": "v3"})

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit", headers={"Authorization": "Bearer secret"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        data = body["entries"]
        assert len(data) == 3
        assert data[0]["action"] == "action3"
        assert data[2]["action"] == "action1"


def test_config_diff_writes_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    from core.config import Config

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        cfg = Config()
        cfg.set("mock_mode", False)

        mtime = cfg.config_path.stat().st_mtime
        content = cfg.config_path.read_text()

        r = client.post("/api/config/diff", headers={"Authorization": "Bearer secret"}, json={"changes": {"mock_mode": True}})
        assert r.status_code == 200
        assert "diff" in r.json()
        assert cfg.config_path.stat().st_mtime == mtime
        assert cfg.config_path.read_text() == content


def test_config_rollback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    from core.config import Config

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        cfg = Config()
        cfg.set("mock_mode", False)

        initial_content = cfg.config_path.read_bytes()

        r = client.post("/api/config", headers={"Authorization": "Bearer secret"}, json={"changes": {"mock_mode": True}})
        assert r.status_code == 200
        backup_id = r.json()["backup_id"]
        assert cfg.config_path.read_bytes() != initial_content

        # Rollback
        r = client.post("/api/config/rollback", headers={"Authorization": "Bearer secret"}, json={"backup_id": backup_id})
        assert r.status_code == 200
        assert cfg.config_path.read_bytes() == initial_content


def test_api_models_get_and_post(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)

        r = client.get("/api/models", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["models"], list)

        # POST custom model
        models_payload = [
            {
                "name": "cliproxy:claude-3-5-sonnet",
                "provider": "cliproxy",
                "model_id": "claude-3-5-sonnet",
                "cost_per_1k_tokens": 0.015,
            }
        ]
        r = client.post("/api/models", headers={"Authorization": "Bearer secret"}, json={"models": models_payload})
        assert r.status_code == 200
        assert r.json()["count"] == 1


def test_api_sync_status():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)
    r = client.get("/api/sync/status")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["bridge_active"] is True
    assert "configured_base_url" in body
    assert "synced_models_count" in body


def test_api_sync_cliproxy(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from scli.web_app import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    client = TestClient(app)

    r = client.post("/api/sync/cliproxy")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert "total_registered" in body


