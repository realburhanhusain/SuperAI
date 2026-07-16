"""CLI inner-model discovery + catalog."""

from core.cli_models import (
    KNOWN_CLI_MODELS,
    list_cli_models_catalog,
    probe_cli_models,
)
from core.member_selection import list_selectable_members
from core.approval_tui import prompt_select_members


def test_probe_cli_models_curated_offline():
    info = probe_cli_models("gemini", live=False, use_cache=False)
    assert info["cli"] == "gemini"
    assert "models" in info
    assert any("gemini" in m.lower() for m in info["models"]) or info["models"]
    assert info["selectors"][0] == "cli:gemini"
    assert any(s.startswith("cli:gemini@") for s in info["selectors"])


def test_known_models_cover_main_clis():
    for name in ("gemini", "claude", "grok", "codex", "aider"):
        assert name in KNOWN_CLI_MODELS
        assert KNOWN_CLI_MODELS[name]


def test_list_cli_models_catalog_shape():
    data = list_cli_models_catalog(only_available=False, live=False, use_cache=False)
    assert data.get("ok") is True
    assert "clis" in data
    assert data["counts"]["clis"] >= 1


def test_list_selectable_includes_cli_model_variants():
    data = list_selectable_members(
        only_available=False, with_cli_models=True, live_cli_models=False
    )
    assert "cli_models" in data
    assert "pick_ids" in data
    assert data["counts"]["cli_model_variants"] >= 0
    # At least bare CLIs or variants appear in pick list
    assert data["pick_ids"]


def test_prompt_select_members_noninteractive(monkeypatch):
    monkeypatch.setenv("SUPERAI_NON_INTERACTIVE", "1")
    opts = ["gpt-4o", "cli:gemini@flash", "cli:grok"]
    picked = prompt_select_members(opts, max_n=2, title="t")
    assert picked == opts[:2]
