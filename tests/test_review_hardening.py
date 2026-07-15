"""Tests for review-hardening fixes (approval, queue, SSRF, redaction, MCP)."""

from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from core.store_lock import WriteQueue, memory_write_queue
from core.net_safety import validate_public_http_url
from core.browser_tool import fetch_page_text
from core.messengers import MessengerBus
from core.tool_proposals import ToolProposalManager
from core.step_cache import StepResultCache


def test_write_queue_timeout_raises():
    q = WriteQueue("test-timeout")

    def hang():
        import time

        time.sleep(5)
        return "ok"

    with pytest.raises(TimeoutError):
        q.submit(hang, timeout=0.05)
    q.close()


def test_ssrf_blocks_localhost():
    err = validate_public_http_url("http://127.0.0.1/admin")
    assert err is not None
    err2 = validate_public_http_url("http://localhost/x")
    assert err2 is not None
    r = fetch_page_text("http://169.254.169.254/latest/meta-data/")
    assert r.get("ok") is False


def test_webhook_blocks_private_url(monkeypatch):
    monkeypatch.setenv("SUPERAI_WEBHOOK_URL", "http://127.0.0.1:9/hook")
    bus = MessengerBus()
    bus.dry_run = False
    r = bus.send("hello", channel="webhook")
    assert r.get("ok") is False or "blocked" in str(r.get("error") or "").lower()


def test_tool_proposal_force_requires_env(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SUPERAI_ALLOW_FORCE_PROPOSALS", raising=False)
    store = ToolProposalManager(store_path=tmp_path / "props.json")
    p = store.propose(
        "run_shell",
        {"command": ["echo", "hi"]},
        rationale="test",
        requires_human=True,
    )
    with pytest.raises(ValueError, match="SUPERAI_ALLOW_FORCE_PROPOSALS"):
        store.execute(p.id, force=True)


def test_step_cache_atomic(tmp_path: Path):
    cache = StepResultCache(path=tmp_path / "step_cache.json")
    cache.put("step-a", {"ok": True}, model="mock")
    assert cache.get("step-a", model="mock") == {"ok": True}
    assert (tmp_path / "step_cache.json").exists()


def test_approval_denial_not_success(monkeypatch):
    from core.model_caller import ModelCaller
    from core.model_registry import ModelRegistry

    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")

    class FakeCfg:
        def get(self, k, default=None):
            if k == "require_human_approval":
                return True
            return default

    monkeypatch.setattr("core.config.Config", lambda: FakeCfg())

    def deny(*a, **k):
        return False

    monkeypatch.setattr("core.approval_tui.prompt_approval", deny)

    # Register a fake cli model
    reg = ModelRegistry()
    # Ensure call path hits external CLI
    mc = ModelCaller(use_mock=False, registry=reg)
    # If no cli: model, skip gracefully
    models = [m for m in (reg.list_models() if hasattr(reg, "list_models") else [])]
    # Direct unit path
    result = mc._call_external_cli("cli:nonexistent-cli-xyz", "do something")
    # When CLI missing, dry-run path (not approval denial) — still should not crash
    assert "status" in result
    # Force approval denial path with available name but require approval
    # Mock available so dry is False
    monkeypatch.setattr(
        "core.external_cli.ExternalCLIRegistry.available",
        lambda self: {"claude": True},
    )
    result2 = mc._call_external_cli("cli:claude", "sensitive task")
    assert result2.get("status") == "error"
    assert result2.get("blocked") is True


def test_databao_sanitize_blocks_sleep():
    from core.databao_adapter import DatabaoAdapter

    # Use mock adapter if constructor needs it
    try:
        ad = DatabaoAdapter(use_mock=True)
    except TypeError:
        ad = DatabaoAdapter()
        ad.use_mock = True
    with pytest.raises(ValueError):
        ad._sanitize_sql("SELECT pg_sleep(10)")
