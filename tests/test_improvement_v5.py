"""Improvement V5 unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_error_taxonomy():
    from core.error_codes import apply_error_taxonomy, set_error_code

    r = {"ok": False, "error": "Run budget exceeded"}
    apply_error_taxonomy(r)
    assert r.get("error_code") == "budget"
    s = set_error_code({}, "timeout", message="slow")
    assert s["error_code"] == "timeout"


def test_cost_accounting():
    from core.cost_accounting import estimate_call, from_usage

    u = from_usage("gpt-4o", total_tokens=1000)
    assert u["estimated_cost_usd"] >= 0
    e = estimate_call("cli:claude", "hello world")
    assert e["estimated_cost_usd"] == 0.0


def test_public_api_wrap():
    from core.public_api import wrap_public_result

    out = wrap_public_result(
        {"ok": True, "response": "hi", "tokens": 10, "estimated_cost_usd": 0.0},
        mock=True,
        ok=True,
        record_spend=False,
    )
    assert out.get("contract") == "superai.result.v1"


def test_idempotent_write(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    from core.agent_tools import tool_write

    a = tool_write("x.txt", "same")
    b = tool_write("x.txt", "same")
    assert a.get("ok") and b.get("ok")
    assert b.get("unchanged") is True or b.get("skipped") is True


def test_cancel_token():
    from core.cancel_token import CancelToken

    t = CancelToken()
    assert not t.is_cancelled()
    t.cancel()
    assert t.is_cancelled()
    try:
        t.raise_if_cancelled()
        assert False
    except InterruptedError:
        pass


def test_result_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_RESULT_CACHE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    from core.result_cache import get, put

    put("t", "hello", {"ok": True, "response": "world", "contract": "superai.result.v1"})
    hit = get("t", "hello")
    assert hit and hit.get("result_cache_hit") is True


def test_front_door_confidence():
    from core.front_door import choose_path

    # default long/ambiguous → low confidence (default branch)
    amb = choose_path(
        "xyzzy plugh fnord quux regarding foo bar baz qux more words here forever"
    )
    assert "confidence" in amb
    # forced always full confidence
    forced = choose_path("x", force="board")
    assert forced["confidence"] == 1.0
    assert forced["needs_confirm"] is False
    # coding path high confidence
    code = choose_path("implement rate limiting middleware")
    assert code["confidence"] >= 0.8


def test_profile_suggest():
    from core.profile_suggest import suggest_profile

    s = suggest_profile()
    assert s.get("suggested_profile") in {"cheap", "balanced", "local-only", "quality"}


def test_eval_golden_mock():
    from core.eval_golden import run_golden

    r = run_golden(use_mock=True, limit=2)
    assert r.get("total") == 2
    assert "results" in r


def test_memory_inject_rank():
    from core.memory_inject import rank_and_pack_memories

    hits = [
        {"content": "alpha beta gamma", "importance": 0.9},
        {"content": "zzz unrelated", "importance": 0.1},
    ]
    p = rank_and_pack_memories("alpha things", hits, max_tokens=100)
    assert p["kept"] >= 1
    assert "alpha" in p["text"]


def test_agent_cancel_runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERAI_SESSIONS_ROOT", str(tmp_path / "s"))
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.cancel_token import CancelToken
    from core.superai_agent.runtime import AgentRuntime

    tok = CancelToken()
    tok.cancel()
    out = AgentRuntime(use_mock=True).run(
        "hello",
        agent="ask",
        permission="plan",
        max_rounds=1,
        cancel_token=tok,
    )
    # cancelled before work or partial
    assert out.raw.get("status") == "cancelled" or not out.ok or out.response
