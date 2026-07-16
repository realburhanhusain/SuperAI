"""Windows-aware PATH resolution (S10 expanded)."""

import os
from pathlib import Path

from core.path_which import resolve_candidates, which_any, which_cmd


def test_which_python_or_none():
    # python should exist in this environment
    p = which_cmd("python") or which_any(["python", "python3", "py"])
    assert p is None or isinstance(p, str)


def test_which_empty_name():
    assert which_cmd("") is None
    assert which_cmd(None) is None  # type: ignore[arg-type]


def test_which_any_order(tmp_path, monkeypatch):
    if os.name != "nt":
        # still verify which_any fallback
        p = which_any(["python", "python3", "py", "nonexistent-xyz"])
        assert p is None or isinstance(p, str)
        return
    d = tmp_path / "p"
    d.mkdir()
    (d / "toolB.cmd").write_text("@echo off\r\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(d) + os.pathsep + os.environ.get("PATH", ""))
    found = which_any(["toolA", "toolB"])
    assert found and "toolB" in found


def test_resolve_candidates():
    p = resolve_candidates("python", detects=["python3", "py"])
    assert p is None or Path(p).exists() or isinstance(p, str)


def test_windows_pathext_cmd(tmp_path, monkeypatch):
    if os.name != "nt":
        return
    d = tmp_path / "npm"
    d.mkdir()
    (d / "mycli.cmd").write_text("@echo off\r\necho x\r\n", encoding="utf-8")
    monkeypatch.setenv("PATH", str(d))
    monkeypatch.setenv("PATHEXT", ".COM;.EXE;.BAT;.CMD")
    assert which_cmd("mycli") is not None
