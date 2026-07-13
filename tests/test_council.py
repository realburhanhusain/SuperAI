"""Council voting modes + config approval flag."""

from pathlib import Path

from superai.core.config import Config
from superai.core.council import Council, parse_vote_mode
from superai.core.model_caller import ModelCaller
from superai.core.model_registry import ModelRegistry


def test_parse_vote_mode():
    assert parse_vote_mode("majority") == "majority"
    assert parse_vote_mode("SUPERVISOR") == "supervisor"
    assert parse_vote_mode("weighted") == "weighted"
    assert parse_vote_mode("nope") == "majority"


def test_council_all_three_modes():
    reg = ModelRegistry()
    caller = ModelCaller(use_mock=True, registry=reg)
    members = reg.list_all_models()[:3] or ["gpt-4o", "claude-4-sonnet", "grok-3"]
    topic = "Should SuperAI default to local-first mock mode?"

    for mode in ("majority", "weighted", "supervisor"):
        c = Council(
            caller=caller,
            registry=reg,
            voting_mode=mode,
            supervisor_model=members[0],
        )
        result = c.run(topic, models=members, voting_mode=mode, with_critique=False)
        assert result["voting_mode"] == mode
        assert result["proposals"]
        assert result["decision"]["mode"] == mode


def test_require_human_approval_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = tmp_path / ".superai" / "config.json"
    path.parent.mkdir(parents=True)
    cfg = Config(config_path=str(path))
    assert cfg.require_human_approval is True
    cfg.set("require_human_approval", False, persist=True)
    cfg2 = Config(config_path=str(path))
    assert cfg2.require_human_approval is False
    cfg2.set("council_voting_mode", "weighted", persist=True)
    cfg3 = Config(config_path=str(path))
    assert cfg3.council_voting_mode == "weighted"
