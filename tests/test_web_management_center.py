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
