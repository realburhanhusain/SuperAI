"""Preferences, time-travel, messengers, web app tests."""

from pathlib import Path

import pytest

from core.messengers import MessengerBus
from core.preferences import UserPreferenceModel
from core.time_travel import FileTimeTravel


def test_preferences_learn_and_infer(tmp_path: Path):
    pm = UserPreferenceModel(path=tmp_path / "prefs.json")
    pm.set("theme", "dark")
    pm.observe_task("coding", "gpt-4o", True, duration=1.0)
    pm.observe_task("coding", "gpt-4o", True, duration=1.0)
    pm.observe_task("coding", "claude-4-sonnet", False, duration=2.0)
    assert pm.get("theme") == "dark"
    assert pm.preferred_model_for("coding") == "gpt-4o"
    summary = pm.profile_summary()
    assert summary["successes"] >= 2


def test_time_travel_snapshot_restore(tmp_path: Path):
    tt = FileTimeTravel(root=tmp_path / "tt")
    f = tmp_path / "work" / "a.txt"
    f.parent.mkdir(parents=True)
    f.write_text("v1", encoding="utf-8")
    s1 = tt.snapshot(f, note="first")
    f.write_text("v2", encoding="utf-8")
    s2 = tt.snapshot(f, note="second")
    assert s2["version"] == 2
    versions = tt.list_versions(f)
    assert len(versions) >= 2
    tt.restore(f, version=1)
    assert f.read_text(encoding="utf-8") == "v1"


def test_messenger_file_channel(tmp_path: Path):
    bus = MessengerBus(path=tmp_path / "log.jsonl")
    r = bus.send("hello bus", channel="file")
    assert r["ok"] is True
    assert (tmp_path / "messenger_outbox.txt").exists()
    recent = bus.recent(5)
    assert recent


def test_web_app_memory_search(tmp_path: Path, monkeypatch):
    pytest.importorskip("fastapi")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # seed a memory
    from core.memory_palace import MemoryPalace

    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    mp = MemoryPalace(persist_directory=str(tmp_path / "mem"))
    mp.store("fastapi routing knowledge", tags=["learning"], metadata={"success": True})

    from fastapi.testclient import TestClient
    from scli.web_app import create_app

    client = TestClient(create_app())
    r = client.get("/api/status")
    assert r.status_code == 200
    r2 = client.get("/api/memory/search", params={"q": "fastapi", "top_k": 5})
    assert r2.status_code == 200
    body = r2.json()
    assert "results" in body
