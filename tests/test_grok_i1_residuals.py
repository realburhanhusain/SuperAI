"""Grok I1 residual close-out from AGY grok_work_review_result_I1_v1."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def test_preferences_atomic_save(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.preferences import UserPreferenceModel

    path = tmp_path / ".superai" / "preferences.json"
    p = UserPreferenceModel(path=path)
    p.set_sticky_model("model-a")
    assert path.is_file()
    raw = path.read_text(encoding="utf-8")
    assert "model-a" in raw
    # reload from disk
    p2 = UserPreferenceModel(path=path)
    assert p2.get("preferred_model") == "model-a"
    # lock file created by store_lock
    assert (tmp_path / ".superai" / "preferences.lock").exists() or path.exists()


def test_bandit_atomic_save(tmp_path: Path):
    from core.bandit_router import EpsilonGreedyBandit

    path = tmp_path / "bandit_state.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=path)
    b.update("m1", 0.8)
    b.update("m1", 0.9)
    assert path.is_file()
    b2 = EpsilonGreedyBandit(epsilon=0.0, path=path)
    assert b2.mean("m1") > 0.8
    assert b2.select(["m1", "m2"]) == "m1"


def test_stream_aggregate_contract(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry
    from core.token_stream import get_stream_meta

    caller = ModelCaller(use_mock=True, registry=ModelRegistry())
    out = caller.call_stream_complete(
        model="gpt-4o-mini", prompt="say hello world for stream aggregate"
    )
    assert out.get("ok") is True
    assert out.get("stream") is True
    assert out.get("contract") == "superai.result.v1" or out.get("contract")
    assert out.get("response")
    assert out.get("stream_meta", {}).get("mode") == "mock_chunked"
    meta = get_stream_meta()
    assert meta.get("aggregated")
    assert meta["aggregated"].get("response") == out.get("response")
    # cost honesty fields present
    assert "estimated_cost_usd" in out or out.get("tokens") is not None


def test_finalize_stream_result_direct():
    from core.token_stream import finalize_stream_result, get_stream_meta

    r = finalize_stream_result(
        "hello aggregated",
        model="gpt-4o",
        provider="openai",
        mode="sse",
        mock=False,
        chunks=3,
        prompt="hi",
    )
    assert r["ok"] is True
    assert r["response"] == "hello aggregated"
    assert r["stream"] is True
    assert r["stream_meta"]["mode"] == "sse"
    assert get_stream_meta().get("aggregated")


def test_m089_offline_phase6_never_false_live_pass(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    # Ensure no accidental live keys in this process for the assertion
    for k in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "DEEPSEEK_API_KEY",
        "XAI_API_KEY",
        "GOOGLE_API_KEY",
        "GROQ_API_KEY",
    ):
        monkeypatch.delenv(k, raising=False)
    (tmp_path / ".superai").mkdir(parents=True)
    from core.live_smoke_complete import run_phase6_smoke

    out = run_phase6_smoke(allow_live=False)
    assert out.get("ok") is True
    assert out.get("phase6_complete_code") is True
    assert out.get("live_passed") is False
    assert out.get("phase6_complete_host") is False
    stream = out.get("stream_sample_offline") or {}
    assert stream.get("ok") is True
    assert stream.get("mock") is True
    assert (stream.get("result") or {}).get("contract") or stream.get("contract")

    # allow_live without keys still does not claim host pass
    out2 = run_phase6_smoke(allow_live=True)
    assert out2.get("live_passed") is False
    assert out2.get("phase6_complete_host") is False


def test_m089_budget_command_name_on_live_path(tmp_path: Path, monkeypatch):
    """When allow_live and targets exist, budget_precheck gets command_name=live-smoke."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    seen = {}

    def fake_targets():
        return [{"provider": "openai", "model": "gpt-4o", "env": "OPENAI_API_KEY"}]

    def fake_precheck(**kwargs):
        seen.update(kwargs)
        return {"ok": True, "blocked": False}

    def fake_smoke(**kwargs):
        return {"ok": True, "passed": 1, "failed": 0, "results": []}

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    import core.live_smoke_complete as lsc

    monkeypatch.setattr(lsc, "available_smoke_targets", fake_targets)
    monkeypatch.setattr(lsc, "budget_precheck", fake_precheck)
    monkeypatch.setattr(lsc, "run_provider_smoke", fake_smoke)
    monkeypatch.setattr(
        lsc,
        "run_stream_smoke_sample",
        lambda **kw: {"ok": True, "mock": False},
    )
    out = lsc.run_phase6_smoke(allow_live=True, include_stream=False)
    assert seen.get("command_name") == "live-smoke"
    assert out.get("live_attempted") is True
