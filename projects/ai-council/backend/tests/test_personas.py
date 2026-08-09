"""Unit tests for backend persona CRUD functions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import backend.personas as personas_module
from backend.personas import (
    DEFAULT_PERSONAS,
    Persona,
    delete_persona_override,
    get_all_personas,
    get_persona,
    get_personas_by_ids,
    save_persona_override,
)


@pytest.fixture(autouse=True)
def isolated_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect the overrides file to a temp path and reset the in-memory cache."""
    overrides_file = tmp_path / "persona_overrides.json"
    monkeypatch.setattr(personas_module, "_OVERRIDES_FILE", overrides_file)
    monkeypatch.setattr(personas_module, "_DATA_DIR", tmp_path)
    # Reset cache so each test starts clean
    monkeypatch.setattr(personas_module, "_overrides_cache", None)
    yield
    # Reset again after test
    monkeypatch.setattr(personas_module, "_overrides_cache", None)


# ── get_all_personas ──────────────────────────────────────────────────────────

def test_get_all_personas_returns_twelve():
    result = get_all_personas()
    assert len(result) == 12


def test_default_personas_include_comedian_and_economist():
    result = get_all_personas()
    ids = {p.id for p in result}
    assert "comedian" in ids
    assert "economist" in ids


def test_default_persona_ids_are_unique():
    ids = [p.id for p in DEFAULT_PERSONAS]
    assert len(ids) == len(set(ids))


def test_default_persona_prompts_include_behavioral_depth():
    for persona in DEFAULT_PERSONAS:
        assert len(persona.system_prompt.split()) >= 60
        assert "Your job is" in persona.system_prompt


def test_get_all_personas_all_are_persona_instances():
    result = get_all_personas()
    assert all(isinstance(p, Persona) for p in result)


def test_get_all_personas_no_customization_by_default():
    result = get_all_personas()
    assert all(not p.is_customized for p in result)


def test_get_all_personas_applies_override():
    save_persona_override("skeptic", {"name": "Super Skeptic"})
    # Reset cache to reload from disk
    personas_module._overrides_cache = None

    result = get_all_personas()
    skeptic = next(p for p in result if p.id == "skeptic")
    assert skeptic.name == "Super Skeptic"
    assert skeptic.is_customized is True


def test_get_all_personas_override_only_affects_one():
    save_persona_override("skeptic", {"name": "Changed"})
    personas_module._overrides_cache = None

    result = get_all_personas()
    others = [p for p in result if p.id != "skeptic"]
    assert all(not p.is_customized for p in others)


# ── get_persona ───────────────────────────────────────────────────────────────

def test_get_persona_valid_id():
    result = get_persona("skeptic")
    assert result is not None
    assert result.id == "skeptic"
    assert result.name == "The Skeptic"


def test_get_persona_invalid_id_returns_none():
    result = get_persona("nonexistent")
    assert result is None


def test_get_persona_applies_override():
    save_persona_override("pragmatist", {"role": "Practical Wizard"})
    personas_module._overrides_cache = None

    result = get_persona("pragmatist")
    assert result is not None
    assert result.role == "Practical Wizard"
    assert result.is_customized is True


def test_get_persona_without_override_not_customized():
    result = get_persona("innovator")
    assert result is not None
    assert result.is_customized is False


# ── get_personas_by_ids ───────────────────────────────────────────────────────

def test_get_personas_by_ids_returns_matching():
    result = get_personas_by_ids(["skeptic", "pragmatist"])
    assert len(result) == 2
    ids = {p.id for p in result}
    assert ids == {"skeptic", "pragmatist"}


def test_get_personas_by_ids_preserves_request_order():
    result = get_personas_by_ids(["innovator", "skeptic"])
    assert result[0].id == "innovator"
    assert result[1].id == "skeptic"


def test_get_personas_by_ids_skips_invalid():
    result = get_personas_by_ids(["skeptic", "ghost", "pragmatist"])
    ids = [p.id for p in result]
    assert "ghost" not in ids
    assert len(result) == 2


def test_get_personas_by_ids_empty_returns_empty():
    result = get_personas_by_ids([])
    assert result == []


# ── save_persona_override ─────────────────────────────────────────────────────

def test_save_persona_override_changes_name():
    result = save_persona_override("skeptic", {"name": "My Skeptic"})
    assert result.name == "My Skeptic"
    assert result.is_customized is True


def test_save_persona_override_persists_to_disk(tmp_path):
    overrides_file = personas_module._OVERRIDES_FILE
    save_persona_override("skeptic", {"name": "Disk Skeptic"})
    assert overrides_file.exists()
    data = json.loads(overrides_file.read_text())
    assert "skeptic" in data
    assert data["skeptic"]["name"] == "Disk Skeptic"


def test_save_persona_override_merges_partial_fields():
    save_persona_override("skeptic", {"name": "First Override"})
    personas_module._overrides_cache = None
    save_persona_override("skeptic", {"role": "Second Override Role"})
    personas_module._overrides_cache = None

    result = get_persona("skeptic")
    assert result.name == "First Override"   # kept from first override
    assert result.role == "Second Override Role"  # from second


def test_save_persona_override_does_not_change_color():
    original = get_persona("skeptic")
    save_persona_override("skeptic", {"name": "Changed"})
    personas_module._overrides_cache = None

    result = get_persona("skeptic")
    assert result.color == original.color


def test_save_persona_override_keeps_default_for_unset_fields():
    original = get_persona("skeptic")
    save_persona_override("skeptic", {"name": "Only Name Changed"})
    personas_module._overrides_cache = None

    result = get_persona("skeptic")
    assert result.role == original.role
    assert result.description == original.description
    assert result.system_prompt == original.system_prompt


# ── delete_persona_override ───────────────────────────────────────────────────

def test_delete_persona_override_restores_defaults():
    original_name = get_persona("skeptic").name
    save_persona_override("skeptic", {"name": "Temporary Name"})
    personas_module._overrides_cache = None

    result = delete_persona_override("skeptic")
    assert result.name == original_name
    assert result.is_customized is False


def test_delete_persona_override_removes_from_disk():
    save_persona_override("skeptic", {"name": "To Delete"})
    personas_module._overrides_cache = None

    delete_persona_override("skeptic")
    personas_module._overrides_cache = None

    overrides_file = personas_module._OVERRIDES_FILE
    if overrides_file.exists():
        data = json.loads(overrides_file.read_text())
        assert "skeptic" not in data


def test_delete_persona_override_nonexistent_is_safe():
    # Deleting a non-customized persona should not raise
    result = delete_persona_override("skeptic")
    assert result.id == "skeptic"
    assert result.is_customized is False


def test_delete_persona_override_only_removes_target():
    save_persona_override("skeptic", {"name": "Keep Pragmatist"})
    save_persona_override("pragmatist", {"name": "Keep Me"})
    personas_module._overrides_cache = None

    delete_persona_override("skeptic")
    personas_module._overrides_cache = None

    pragmatist = get_persona("pragmatist")
    assert pragmatist.name == "Keep Me"
    assert pragmatist.is_customized is True
