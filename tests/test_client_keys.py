"""C6.5 — client_keys credential store: minting, scoping, and on-disk hardening."""

import json
import os
import sys
from pathlib import Path

import pytest


def _mgr(tmp_path, monkeypatch):
    # client_keys resolves via Path.home(), not os.path.expanduser, so this
    # monkeypatch genuinely isolates it. (The reverse case is the documented
    # CI-hang trap in this repo — check which mechanism a module uses.)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.client_keys import ClientKeyManager

    return ClientKeyManager()


def test_mint_produces_a_strong_scoped_key(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    key = m.mint_key("agent-a", token_budget=100, allowed_models=["gpt-4o"], expires_in_days=1)

    assert key.startswith("sk-sai-")
    assert len(key) > 40, "secrets.token_urlsafe(32) should give plenty of entropy"

    v = m.validate_key(key, requested_model="gpt-4o")
    assert v["ok"] is True
    assert v["key_data"]["name"] == "agent-a"


def test_scope_and_budget_are_enforced(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    key = m.mint_key("agent-b", token_budget=100, allowed_models=["gpt-4o"])

    assert m.validate_key(key, requested_model="claude-3")["ok"] is False
    assert m.validate_key(key, estimated_tokens=101)["ok"] is False
    assert m.validate_key(key, estimated_tokens=50)["ok"] is True

    assert m.validate_key("sk-sai-not-a-real-key")["ok"] is False


def test_revoke_then_reject(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    key = m.mint_key("agent-c")
    assert m.validate_key(key)["ok"] is True

    assert m.revoke_key(key) is True
    assert m.validate_key(key)["ok"] is False
    assert m.revoke_key("sk-sai-nope") is False


def test_consume_budget_accumulates_and_persists(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    key = m.mint_key("agent-d", token_budget=100)

    m.consume_budget(key, 30)
    m.consume_budget(key, 30)

    from core.client_keys import ClientKeyManager

    reloaded = ClientKeyManager()  # separate instance = proves it round-tripped to disk
    assert reloaded.validate_key(key)["key_data"]["tokens_used"] == 60
    assert reloaded.validate_key(key, estimated_tokens=50)["ok"] is False, "60+50 > 100"


def test_listing_redacts_the_secret(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    key = m.mint_key("agent-e")

    listed = m.list_keys()
    assert len(listed) == 1
    assert key not in json.dumps(listed), "the full key must never appear in a listing"
    assert "..." in listed[0]["id"]


def test_store_is_written_atomically_with_a_backup(tmp_path, monkeypatch):
    """C6.5: the credential file uses the T06 helper, not a bare write_text."""
    m = _mgr(tmp_path, monkeypatch)
    m.mint_key("agent-f")
    m.mint_key("agent-g")  # second write triggers backup rotation of the first

    assert m.config_path.exists()
    backups = list((tmp_path / ".superai" / "backups").glob("client_keys-*.json"))
    assert backups, "second write should have rotated a backup of the previous file"

    # no partial/truncated file left behind
    json.loads(m.config_path.read_text(encoding="utf-8"))


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not meaningful on Windows")
def test_store_is_owner_only(tmp_path, monkeypatch):
    m = _mgr(tmp_path, monkeypatch)
    m.mint_key("agent-h")
    assert (m.config_path.stat().st_mode & 0o777) == 0o600


def test_validation_is_constant_time_by_construction(tmp_path, monkeypatch):
    """
    Not a timing measurement — those are flaky. Asserts the *mechanism*:
    lookup goes through hmac.compare_digest against every stored key rather
    than a dict hash lookup that short-circuits on the key material.
    """
    import inspect

    from core.client_keys import ClientKeyManager

    src = inspect.getsource(ClientKeyManager._match_key)
    assert "compare_digest" in src

    m = _mgr(tmp_path, monkeypatch)
    real = m.mint_key("agent-i")
    assert m._match_key(real) == real
    assert m._match_key(real[:-1] + ("x" if real[-1] != "x" else "y")) is None
    assert m._match_key("") is None
