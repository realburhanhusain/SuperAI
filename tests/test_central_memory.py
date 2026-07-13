"""Central Memory Palace for SuperAI-mediated AIs."""

from pathlib import Path

from core.central_memory import (
    inject_context,
    memory_preface_for_llm,
    status,
    write_back,
    write_back_workflow,
    central_memory_enabled,
)
from core.council import Council
from core.cli_pool import ParallelCLIManager
from core.memory_palace import MemoryPalace


def test_central_memory_defaults_on(monkeypatch):
    monkeypatch.delenv("SUPERAI_CENTRAL_MEMORY", raising=False)
    assert central_memory_enabled() is True


def test_inject_and_write_back(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    # Default MemoryPalace uses ~/.superai/memory under patched home
    MemoryPalace().store(
        "Past learning: prefer FastAPI for small HTTP services.",
        tags=["learning", "coding"],
        metadata={"success": True},
    )

    ctx = inject_context("build a small HTTP API", prompt="implement it")
    assert ctx["enabled"] is True
    assert "User request" in ctx["prompt"] or "implement" in ctx["prompt"]

    wb = write_back(
        task="build a small HTTP API",
        source="test",
        model_or_cli="cli:test",
        success=True,
        latency=0.1,
        output="created app.py with FastAPI",
        context_id=ctx.get("context_id"),
        tags=["test"],
    )
    assert wb.get("ok") is True
    assert wb.get("learning_id") or wb.get("ingest_id")


def test_write_back_skipped_when_disabled(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_CENTRAL_MEMORY", "0")
    wb = write_back(
        task="x",
        source="test",
        model_or_cli="m",
        success=True,
        output="y",
    )
    assert wb.get("skipped") is True


def test_workflow_write_back(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    r = write_back_workflow(
        task="multi worker task",
        source="cli_pool",
        workflow_id="wf-test",
        succeeded=2,
        failed=0,
        total=2,
        synthesis="merged plan",
        jobs=[
            {"cli": "claude", "status": "done", "stdout_tail": "ok1"},
            {"cli": "aider", "status": "done", "stdout_tail": "ok2"},
        ],
    )
    assert r.get("ok") is True


def test_cli_pool_writes_memory(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    mgr = ParallelCLIManager(path=tmp_path / ".superai" / "cli_jobs.json")
    result = mgr.run_parallel(
        [{"cli": "claude", "prompt": "design widget", "role": "architect"}],
        dry_run=True,
        auto_approve=True,
        with_context=True,
    )
    assert result.get("central_memory") is True
    assert "memory_write" in result


def test_council_memory_flag(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir()
    MemoryPalace().store(
        "Council past: prefer majority for simple topics.",
        tags=["learning"],
    )
    out = Council().run("Should we use majority voting?", models=None)
    assert "memory_injected" in out
    assert "memory_write" in out or out.get("decision")


def test_status_shape(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    s = status()
    assert s["enabled"] is True
    assert s["store"] == "MemoryPalace"
    assert "opt_out" in s


def test_memory_preface(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    (tmp_path / ".superai").mkdir(parents=True)
    MemoryPalace().store(
        "Use pytest for unit tests always.",
        tags=["learning", "testing"],
    )
    text = memory_preface_for_llm("how should we test?")
    assert isinstance(text, str)
    assert "Memory Palace" in text or text == ""
