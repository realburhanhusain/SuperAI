"""G2 M068/M050: preference bias + bandit continuous product pipeline."""

import random
from pathlib import Path

import pytest

from core.bandit_router import EpsilonGreedyBandit, route_candidates
from core.preferences import UserPreferenceModel

pytestmark = pytest.mark.unit


@pytest.fixture
def pref_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    return tmp_path / ".superai" / "preferences.json"


def test_bias_preferred_first(pref_path: Path):
    p = UserPreferenceModel(path=pref_path)
    p.set_sticky_model("claude-4-sonnet")
    ordered = p.bias_candidates(["gpt-4o", "claude-4-sonnet", "mini"])
    assert ordered[0] == "claude-4-sonnet"
    assert set(ordered) == {"gpt-4o", "claude-4-sonnet", "mini"}


def test_bias_cheap_mode(pref_path: Path):
    p = UserPreferenceModel(path=pref_path)
    p.set_sticky_cheap(True)
    ordered = p.bias_candidates(["gpt-4o", "gpt-4o-mini", "deepseek-chat"])
    assert ordered[0] == "gpt-4o-mini"


def test_bias_empty_candidates(pref_path: Path):
    p = UserPreferenceModel(path=pref_path)
    assert p.bias_candidates([]) == []


def test_route_candidates_prefs_then_bandit(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    p = UserPreferenceModel(path=tmp_path / ".superai" / "preferences.json")
    p.set_sticky_model("model-b")
    bandit_path = tmp_path / ".superai" / "bandit_state.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=bandit_path)
    for _ in range(8):
        b.update("model-a", 0.99)
        b.update("model-b", 0.1)
    # Prefs pin B first; bandit with epsilon=0 should then pick A if both candidates
    out = route_candidates(
        ["model-c", "model-a", "model-b"],
        apply_preferences=True,
        apply_bandit=True,
        epsilon=0.0,
        bandit_path=bandit_path,
    )
    assert out["ok"] is True
    assert "preferences.bias_candidates" in out["stages"]
    assert "bandit.select" in out["stages"]
    # After prefs, model-b is first; bandit select among [b,c,a] with high A reward
    # should put A first when epsilon=0
    assert out["selected"] == "model-a"
    assert out["order"][0] == "model-a"


def test_bandit_update_persists_and_select(tmp_path: Path):
    path = tmp_path / "bandit.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=path)
    b.update("x", 0.2)
    b.update("y", 0.9)
    b2 = EpsilonGreedyBandit(epsilon=0.0, path=path)
    assert b2.select(["x", "y"]) == "y"
    st = b2.status()
    assert st["arm_count"] == 2
    assert st["arms"][0]["model"] == "y"
    b2.reset()
    assert b2.status()["arm_count"] == 0


def test_bandit_reward_from_outcome():
    high = EpsilonGreedyBandit.reward_from_outcome(
        True, latency=0.1, cost=0.0, user_satisfaction=1.0
    )
    low = EpsilonGreedyBandit.reward_from_outcome(
        False, latency=10.0, cost=1.0, user_satisfaction=0.0
    )
    assert high > low


def test_model_caller_uses_bias_candidates(tmp_path: Path, monkeypatch):
    """Integration: ModelCaller.call reorders failover via route_candidates/prefs."""
    # route_candidates runs the bandit with epsilon=0.1, and EpsilonGreedyBandit
    # explores via an unseeded random.random() (bandit_router.py:54). This test
    # asserts a deterministic first pick, so exploration has to be off: without
    # this the test fails whenever exploration fires and picks something other
    # than the preferred arm — measured at 2 failures in 40 runs.
    # Forcing exploitation here rather than lowering the production epsilon: the
    # randomness is the algorithm working as designed, the assertion is what
    # needs pinning.
    monkeypatch.setattr(random, "random", lambda: 1.0)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    p = UserPreferenceModel(path=tmp_path / ".superai" / "preferences.json")
    p.set_sticky_model("mock-preferred")

    class FakeReg:
        def get_model(self, name):
            return type(
                "M",
                (),
                {
                    "name": name,
                    "provider": "mock",
                    "model_id": name,
                    "cost_per_1k_tokens": 0.0,
                    "latency_tier": 2,
                },
            )()

        def list_all_models(self):
            return ["a", "mock-preferred", "b"]

    def fake_escalate(model, **kwargs):
        return ["a", "mock-preferred", "b"]

    monkeypatch.setattr("core.local_first.escalate_chain", fake_escalate)
    monkeypatch.setattr(
        "core.local_first.profile_flags",
        lambda: {"prefer_local": False, "prefer_open_weight": False, "local_only": False},
    )

    seen_orders = []
    tried_models = []

    from core.model_caller import ModelCaller

    caller = ModelCaller(use_mock=True, registry=FakeReg())

    import core.bandit_router as br

    real_route = br.route_candidates

    def tracking_route(cands, **kwargs):
        out = real_route(cands, **kwargs)
        seen_orders.append(list(out.get("order") or []))
        return out

    monkeypatch.setattr(br, "route_candidates", tracking_route)

    def fake_one(self, model, **kwargs):
        tried_models.append(str(model))
        return {
            "ok": True,
            "status": "success",
            "response": "ok",
            "mock": True,
            "model": model,
        }

    monkeypatch.setattr(ModelCaller, "_call_one_model", fake_one)

    out = caller.call(model="a", prompt="test routing bias", use_fallback=True)
    assert out is not None
    assert seen_orders, "route_candidates should run on ModelCaller.call"
    assert seen_orders[-1][0] == "mock-preferred"
    assert tried_models, "should attempt at least one model"
    assert tried_models[0] == "mock-preferred"

    routed = route_candidates(
        ["a", "mock-preferred", "b"],
        apply_bandit=False,
    )
    assert routed["order"][0] == "mock-preferred"


def test_bandit_select_single_epsilon(tmp_path: Path, monkeypatch):
    """P1.4: select() is the sole epsilon gate (no outer double-roll)."""
    from core.bandit_router import EpsilonGreedyBandit

    path = tmp_path / "b.json"
    b = EpsilonGreedyBandit(epsilon=0.0, path=path)
    for _ in range(5):
        b.update("high", 1.0)
        b.update("low", 0.0)
    # With epsilon=0 always exploit high
    picks = [b.select(["low", "high"]) for _ in range(20)]
    assert all(p == "high" for p in picks)


def test_profile_summary_path(pref_path: Path):
    p = UserPreferenceModel(path=pref_path)
    p.set_sticky_model("m1")
    p.set_sticky_cheap(True)
    s = p.profile_summary()
    assert s["sticky_model"] == "m1"
    assert s["cheap_mode"] is True
    assert "preferences.json" in s["path"] or s["path"].endswith("preferences.json")
    assert "pipeline" in s


def test_bandit_ignores_replayed_outcome_event(tmp_path: Path):
    bandit = EpsilonGreedyBandit(path=tmp_path / "bandit.json")
    assert bandit.update("model-a", 1.0, event_id="run-42") is True
    assert bandit.update("model-a", 1.0, event_id="run-42") is False
    assert bandit.state["model-a"]["n"] == 1