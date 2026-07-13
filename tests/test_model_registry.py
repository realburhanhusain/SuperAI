"""Model registry JSON loading tests."""

import json
from pathlib import Path

from superai.core.model_registry import ModelRegistry


def test_load_from_models_json(tmp_path: Path):
    models = [
        {
            "name": "test-model",
            "provider": "openai",
            "model_id": "gpt-test",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY",
            "strengths": "testing",
        }
    ]
    path = tmp_path / "models.json"
    path.write_text(json.dumps(models), encoding="utf-8")

    reg = ModelRegistry(models_path=path)
    assert reg.get_model("test-model") is not None
    assert reg.get_model("test-model").model_id == "gpt-test"
    assert "test-model" in reg.list_all_models()
    assert reg.source == str(path)


def test_builtin_fallback_when_missing(tmp_path: Path):
    missing = tmp_path / "nope.json"
    reg = ModelRegistry(models_path=missing)
    # Falls back to builtin
    assert len(reg.list_all_models()) >= 1
    assert reg.source == "builtin"
