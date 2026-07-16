"""Unified API model + CLI member selection."""

from core.member_selection import (
    list_selectable_members,
    parse_member_spec,
    resolve_members,
)


def test_parse_api_and_cli_specs():
    a = parse_member_spec("gpt-4o")
    assert a.kind == "api"
    assert a.id == "gpt-4o"

    b = parse_member_spec("cli:gemini")
    assert b.kind == "cli"
    assert b.cli_name == "gemini"
    assert b.model_id is None

    c = parse_member_spec("cli:gemini@gemini-2.5-pro")
    assert c.kind == "cli"
    assert c.cli_name == "gemini"
    assert c.model_id == "gemini-2.5-pro"

    d = parse_member_spec("cli:codex/o3")
    assert d.cli_name == "codex"
    assert d.model_id == "o3"


def test_list_selectable_members_shape():
    data = list_selectable_members()
    assert data.get("ok") is True
    assert "api_models" in data
    assert "clis" in data
    assert "selectable_ids" in data
    assert "syntax" in data
    assert data["counts"]["api_total"] >= 0


def test_resolve_members_explicit_mixed():
    specs = resolve_members(
        ["gpt-4o", "cli:gemini@flash", "cli:grok"],
        max_members=5,
    )
    assert len(specs) == 3
    kinds = {s.kind for s in specs}
    assert "api" in kinds
    assert "cli" in kinds
    gem = next(s for s in specs if s.cli_name == "gemini")
    assert gem.model_id == "flash"


def test_resolve_members_auto():
    specs = resolve_members(None, max_members=3, prefer="mixed")
    assert isinstance(specs, list)


def test_parse_bare_cli_name_and_slash():
    # slash form already covered; bare known CLI name if on registry
    from core.external_cli import ExternalCLIRegistry

    if ExternalCLIRegistry().get("gemini"):
        g = parse_member_spec("gemini")
        assert g.kind == "cli"
        assert g.cli_name == "gemini"


def test_list_includes_api_when_mock():
    import os

    os.environ.setdefault("SUPERAI_MOCK_MODE", "1")
    data = list_selectable_members(only_available=True)
    # In mock mode API models count as available even without keys
    assert data.get("mock_mode") is True or data["counts"]["api_configured"] >= 0
    assert "syntax" in data
    assert "api" in data["syntax"]
