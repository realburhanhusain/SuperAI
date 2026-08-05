import os
import pytest
from fastapi.testclient import TestClient
from unittest import mock

from cli.web_app import create_app

def test_flag_off_route_absent():
    with mock.patch.dict(os.environ, {"SUPERAI_WEB_ENABLE_CONFIG_WRITE": "0"}):
        app = create_app()
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/api/config" not in routes

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
