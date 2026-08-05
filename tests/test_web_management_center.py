from __future__ import annotations









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

    # Fake a running daemon
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









from fastapi.testclient import TestClient
from scli.web_app import create_app

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
from scli.web_app import create_app
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

import os
import pytest
from fastapi.testclient import TestClient
from unittest import mock

from scli.web_app import create_app

def test_flag_on_token_unset_route_absent_and_logs(caplog):
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1"}, clear=True):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/config" not in routes
        assert "SUPERAI_WEB_ENABLE_CONFIG_WRITE is on but SUPERAI_WEB_MANAGEMENT_TOKEN is unset" in caplog.text

def test_flag_on_token_set_request_without_token_on_loopback_refused():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", json={"some": "data"})
        assert response.status_code == 401
        assert "Management token required" in response.json().get("detail", "")

def test_wrong_token_refused():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer badtoken"}, json={"some": "data"})
        assert response.status_code == 401
        assert "Unauthorized management token" in response.json().get("detail", "")

def test_correct_token_accepted():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer secret"}, json={"some": "data"})
        assert response.status_code == 200

def test_superai_web_token_does_not_grant_write_access():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret", "SUPERAI_WEB_TOKEN": "regular"}):
        app = create_app()
        client = TestClient(app)
        response = client.post("/api/config", headers={"Authorization": "Bearer regular"}, json={"some": "data"})
        assert response.status_code == 401



def test_console_page():
    from scli.web_app import create_app
    from fastapi.testclient import TestClient
    app = create_app()
    client = TestClient(app)
    r = client.get("/console")
    assert r.status_code == 200
    assert "SuperAI Console" in r.text

def test_api_audit_missing_token_refused():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit")
        assert response.status_code == 401

def test_api_audit_read_token_refused():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret", "SUPERAI_WEB_TOKEN": "regular"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit", headers={"Authorization": "Bearer regular"})
        assert response.status_code == 401

def test_api_audit_missing_file_returns_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        response = client.get("/api/audit", headers={"Authorization": "Bearer secret"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["entries"] == []

def test_api_audit_returns_entries_newest_first_and_respects_limit(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    from core.audit_log import AuditLog
    audit = AuditLog()
    audit.record("action1", detail={"k": "v1"})
    audit.record("action2", detail={"k": "v2"})
    audit.record("action3", detail={"k": "v3"})
    
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        
        # Default limit
        response = client.get("/api/audit", headers={"Authorization": "Bearer secret"})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        data = body["entries"]
        assert len(data) == 3
        assert data[0]["action"] == "action3"
        assert data[2]["action"] == "action1"
        
        # Limit 2
        response2 = client.get("/api/audit?limit=2", headers={"Authorization": "Bearer secret"})
        body2 = response2.json()
        data2 = body2["entries"]
        assert len(data2) == 2
        assert data2[0]["action"] == "action3"
        assert data2[1]["action"] == "action2"


def test_config_diff_writes_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        from core.config import Config
        cfg = Config()
        cfg.set("mock_mode", False)
        
        mtime = cfg.config_path.stat().st_mtime
        content = cfg.config_path.read_text()
        
        r = client.post("/api/config/diff", headers={"Authorization": "Bearer secret"}, json={"changes": {"mock_mode": True}})
        assert r.status_code == 200
        assert "diff" in r.json()
        
        assert cfg.config_path.stat().st_mtime == mtime
        assert cfg.config_path.read_text() == content


def test_config_backups_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        r = client.get("/api/config/backups", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200
        assert r.json()["backups"] == []

def test_config_rollback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        from core.config import Config
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

def test_config_rollback_path_traversal(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        
        r = client.post("/api/config/rollback", headers={"Authorization": "Bearer secret"}, json={"backup_id": "../../../etc/passwd"})
        assert r.status_code == 400
        assert "invalid backup_id" in r.json()["detail"]

def test_config_rollback_creates_own_backup(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        from core.config import Config
        cfg = Config()
        cfg.save()
        
        r1 = client.post("/api/config", headers={"Authorization": "Bearer secret"}, json={"changes": {"mock_mode": True}})
        backup_id = r1.json()["backup_id"]
        
        # Now rollback
        r = client.post("/api/config/rollback", headers={"Authorization": "Bearer secret"}, json={"backup_id": backup_id})
        assert r.status_code == 200
        
        r_list = client.get("/api/config/backups", headers={"Authorization": "Bearer secret"})
        backups = r_list.json()["backups"]
        assert len(backups) == 2

def test_config_routes_auth_and_flags():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "0"}):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/config/diff" not in routes
        assert "/api/config/backups" not in routes
        assert "/api/config/rollback" not in routes


def test_api_models_get(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        
        # Test GET
        r = client.get("/api/models", headers={"Authorization": "Bearer secret"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["models"], list)
        assert len(data["models"]) > 0
        
        # Verify provenance field is present
        assert "source_file" in data["models"][0]
        assert isinstance(data["models"][0]["source_file"], str)

def test_api_models_post(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        
        # Repo models.json path
        repo_models = Path(__file__).resolve().parents[1] / "config" / "models.json"
        if repo_models.exists():
            repo_hash_before = repo_models.read_bytes()
        else:
            repo_hash_before = b""
        
        # Test POST
        models_payload = [
            {
                "name": "my-custom-model",
                "provider": "openai",
                "model_id": "gpt-4",
                "cost_per_1k_tokens": 0.03
            }
        ]
        r = client.post("/api/models", headers={"Authorization": "Bearer secret"}, json={"models": models_payload})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["count"] == 1
        
        # Verify user file is created
        user_models = tmp_path / ".superai" / "config" / "models.json"
        assert user_models.exists()
        
        import json
        saved = json.loads(user_models.read_text())
        assert len(saved) == 1
        assert saved[0]["name"] == "my-custom-model"
        
        # Test proves the repo-tracked config/models.json is byte-identical after a POST
        if repo_models.exists():
            repo_hash_after = repo_models.read_bytes()
            assert repo_hash_before == repo_hash_after

def test_api_models_post_validation(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "1", "SUPERAI_WEB_MANAGEMENT_TOKEN": "secret"}):
        app = create_app()
        client = TestClient(app)
        
        # Unknown field
        bad_payload = [
            {
                "name": "my-model",
                "unknown_field": "123"
            }
        ]
        r = client.post("/api/models", headers={"Authorization": "Bearer secret"}, json={"models": bad_payload})
        assert r.status_code == 400
        assert "unknown fields" in r.text
        
        # Wrong type
        bad_payload2 = [
            {
                "name": "my-model",
                "context_window": "not-an-int"
            }
        ]
        r = client.post("/api/models", headers={"Authorization": "Bearer secret"}, json={"models": bad_payload2})
        assert r.status_code == 400
        assert "type conversion error" in r.text

def test_cliproxy_admin_route_requires_opt_in():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN": "0"}):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/cliproxy-admin" not in routes

    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN": "1"}):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/cliproxy-admin" in routes

