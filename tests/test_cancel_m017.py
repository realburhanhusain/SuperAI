"""M017 — cooperative cancel across model/agent/board/council paths."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_token_basics():
    from core.cancel_token import CancelToken

    t = CancelToken(name="t")
    assert not t.is_cancelled()
    assert t.check() is True
    t.cancel("user")
    assert t.is_cancelled()
    assert t.reason == "user"
    with pytest.raises(InterruptedError):
        t.raise_if_cancelled()


def test_using_restores_previous():
    from core.cancel_token import CancelToken, current, set_current, using

    set_current(None)
    outer = CancelToken(name="outer")
    set_current(outer)
    with using(CancelToken(name="inner")) as inner:
        assert current() is inner
        assert current().name == "inner"
    assert current() is outer
    set_current(None)


def test_cancelled_envelope_contract():
    from core.cancel_token import cancelled_envelope

    env = cancelled_envelope(reason="stop")
    assert env.get("ok") is False
    assert env.get("error_code") == "cancelled"
    assert env.get("status") == "cancelled"
    assert env.get("contract")
    assert env.get("cancelled") is True


def test_pre_call_blocked_when_cancelled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from core.call_lifecycle import pre_call
    from core.cancel_token import CancelToken, set_current

    tok = CancelToken()
    tok.cancel()
    set_current(tok)
    try:
        out = pre_call("gpt-4o", "hi", skip_budget=True)
        assert out.get("blocked") or out.get("status") == "cancelled"
        assert out.get("error_code") == "cancelled" or out.get("cancelled")
    finally:
        set_current(None)


def test_map_cooperative_marks_cancelled():
    from core.cancel_token import CancelToken, map_cooperative, set_current

    tok = CancelToken(name="map")
    set_current(tok)
    seen = []

    def work(n: int):
        seen.append(n)
        if n == 0:
            tok.cancel("mid")
        return {"ok": True, "n": n}

    outs = map_cooperative([0, 1, 2, 3, 4], work, max_workers=2, token=tok)
    set_current(None)
    assert len(outs) == 5
    assert tok.is_cancelled()
    assert any(isinstance(o, dict) and o.get("cancelled") for o in outs)


def test_model_caller_respects_cancel(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.cancel_token import CancelToken, set_current
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    tok = CancelToken()
    tok.cancel()
    set_current(tok)
    try:
        out = ModelCaller(use_mock=True, registry=ModelRegistry()).call(
            model="gpt-4o-mini", prompt="x", use_fallback=False
        )
        assert (
            out.get("status") == "cancelled"
            or out.get("blocked")
            or out.get("error_code") == "cancelled"
            or out.get("ok") is False
        )
    finally:
        set_current(None)


def test_agent_runtime_cancel(tmp_path, monkeypatch):
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
    assert out.raw.get("status") == "cancelled" or not out.ok


def test_board_honors_pre_cancelled_token(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.cancel_token import CancelToken, set_current
    from core.multi_cli_advisory import multi_cli_board

    tok = CancelToken()
    tok.cancel("board_stop")
    set_current(tok)
    try:
        out = multi_cli_board(
            "should we ship?",
            members=["gpt-4o-mini", "deepseek-chat"],
            dry_run=True,
            use_cache=False,
            max_clis=2,
        )
        assert (
            out.get("cancelled")
            or out.get("status") == "cancelled"
            or any(
                isinstance(o, dict) and o.get("cancelled")
                for o in (out.get("opinions") or [])
            )
        )
    finally:
        set_current(None)


def test_council_stops_when_cancelled(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    from core.cancel_token import CancelToken, set_current
    from core.council import Council
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    class OnceThenCancel(ModelCaller):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.n = 0

        def call(self, model, prompt, **kwargs):
            self.n += 1
            if self.n >= 1:
                from core.cancel_token import cancel_current

                cancel_current("after_first")
            return super().call(model, prompt, **kwargs)

    tok = CancelToken()
    set_current(tok)
    try:
        c = Council(caller=OnceThenCancel(use_mock=True, registry=ModelRegistry()))
        out = c.run("pick a color", models=["gpt-4o-mini", "deepseek-chat", "gemini-2.0-flash"])
        assert (
            out.get("status") == "cancelled"
            or out.get("error_code") == "cancelled"
            or out.get("cancelled")
            or len(out.get("proposals") or []) < 3
        )
    finally:
        set_current(None)


def test_audit_m017():
    from core.cancel_token import audit_m017

    out = audit_m017()
    assert out.get("ok") is True, out.get("issues")
    assert out.get("contract")
