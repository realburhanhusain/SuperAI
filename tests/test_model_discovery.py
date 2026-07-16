"""Ollama sync + register model helpers."""

from pathlib import Path

from core.model_discovery import (
    ollama_tags_to_catalog,
    provider_status,
    register_openai_compatible_model,
    sync_ollama_to_user_registry,
)


def test_ollama_tags_to_catalog():
    tags = [{"name": "llama3.2:latest"}, {"name": "gemma2:9b"}]
    cat = ollama_tags_to_catalog(tags, use_openai_compat=True)
    assert len(cat) == 2
    assert cat[0]["provider"] == "ollama_openai"
    assert cat[0]["model_id"] == "llama3.2:latest"
    assert cat[0]["name"].startswith("ollama/")


def test_provider_status():
    st = provider_status()
    assert st["ok"] is True
    assert st["counts"]["total"] >= 10
    assert "nvidia" in st["openai_compat_ids"]


def test_register_model_writes_user_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "config").mkdir(parents=True)
    out = register_openai_compatible_model(
        "my-local-7b",
        "7b-instruct",
        provider="vllm",
        base_url="http://10.0.0.5:8000/v1",
        api_key_env=None,
        write=True,
    )
    assert out["ok"] is True
    path = Path(out["written_to"])
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "my-local-7b" in text
    assert "10.0.0.5" in text


def test_sync_ollama_empty_ok_structure(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai" / "config").mkdir(parents=True)
    monkeypatch.setattr(
        "core.model_discovery.list_ollama_tags",
        lambda **kw: [],
    )
    meta = sync_ollama_to_user_registry(write=True)
    assert "ollama_tags" in meta
    assert meta.get("discovered") == 0
