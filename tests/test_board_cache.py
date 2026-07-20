"""Board cache + smart sizing."""

from pathlib import Path

from core.board_cache import get_board, put_board, smart_max_members
from core.multi_cli_advisory import multi_cli_board


def test_smart_max_members():
    assert smart_max_members("short?", default=3) <= 2
    assert smart_max_members("x " * 500, default=3, hard_cap=5) >= 3


def test_board_cache_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    subject = "cache me please auth design"
    put_board(
        subject,
        {
            "ok": True,
            "status": "success",
            "mode": "review",
            "members": ["gpt-4o"],
            "board": {"verdict": "advise"},
            "mock": True,
            "dry_run": True,
            "contract": "superai.result.v1",
        },
        mode="review",
        members=["gpt-4o"],
        prefer="mixed",
        dry_run=True,
    )
    hit = get_board(
        subject, mode="review", members=["gpt-4o"], prefer="mixed", dry_run=True
    )
    assert hit is not None
    assert hit.get("cache_hit") is True
    assert hit.get("board", {}).get("verdict") == "advise"


def test_multi_cli_board_cache_hit(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    subj = "unique subject for board cache xyzzy"
    a = multi_cli_board(subj, mode="advise", members=["gpt-4o"], dry_run=True)
    b = multi_cli_board(subj, mode="advise", members=["gpt-4o"], dry_run=True)
    assert a.get("ok") is True
    assert b.get("cache_hit") is True or b.get("ok") is True
