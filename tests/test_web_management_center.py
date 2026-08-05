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
