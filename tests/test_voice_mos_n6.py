"""MOS-N6 — Voice hooks full path (offline, no mic required)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_voice_status_and_backends(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import list_backends, status

    st = status()
    assert st.get("ok") is True
    assert "enabled" in st
    assert "/listen" in str(st.get("commands"))
    b = list_backends()
    assert "mock" in (b.get("tts") or [])
    assert "file" in (b.get("stt") or [])


def test_speak_mock_outbox(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import speak

    r = speak("hello superai", force_backend="mock")
    assert r.get("ok") is True
    assert r.get("backend") == "mock"
    out = tmp_path / ".superai" / "voice_out.txt"
    assert out.is_file()
    assert "hello" in out.read_text(encoding="utf-8")


def test_speak_empty_skipped(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import speak

    r = speak("")
    assert r.get("ok") is True
    assert r.get("skipped") is True


def test_queue_and_listen_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import listen_once, queue_voice_text

    q = queue_voice_text("review the login bug")
    assert q.get("ok") is True
    L = listen_once(timeout=0.1, prefer_file=True)
    assert L.get("ok") is True
    assert "login" in str(L.get("text") or "")
    assert L.get("backend") == "file"
    # consumed
    L2 = listen_once(timeout=0.1, prefer_file=True)
    assert L2.get("ok") is False


def test_handle_voice_slash_config(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import handle_voice_slash, load_config

    assert handle_voice_slash("on").get("ok") is True
    assert handle_voice_slash("auto on").get("ok") is True
    cfg = load_config()
    assert cfg.get("enabled") is True
    assert cfg.get("auto_speak_replies") is True
    assert handle_voice_slash("auto off").get("ok") is True
    assert load_config().get("auto_speak_replies") is False
    assert handle_voice_slash("queue test phrase").get("ok") is True
    assert handle_voice_slash("backends").get("ok") is True


def test_speak_reply_respects_auto(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import save_config, speak_reply

    save_config({"auto_speak_replies": False, "enabled": True})
    r = speak_reply("should skip", force=False)
    assert r.get("skipped") is True
    r2 = speak_reply("force me", force=True)
    # force uses speak → mock on systems without pyttsx3
    assert r2.get("ok") is True or r2.get("backend")


def test_voice_disabled(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import handle_voice_slash, speak

    handle_voice_slash("off")
    r = speak("x", force_backend="mock")
    assert r.get("ok") is False
    assert r.get("error") == "voice_disabled"


def test_moscow_n6_compat(tmp_path, monkeypatch):
    """Original MoSCoW test shape still holds with richer module."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.voice_io import listen_once, speak

    s = speak("")
    assert isinstance(s, dict) and "ok" in s
    L = listen_once(timeout=0.1)
    assert isinstance(L, dict) and "ok" in L
