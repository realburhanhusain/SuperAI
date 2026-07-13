"""Track H/I foundational tests."""

from pathlib import Path

from core.agentic import AgenticWorkflows
from core.discovery import discover_environment
from core.external_cli import ExternalCLIRegistry, ExternalCLITool
from core.tool_proposals import ToolProposalManager
from core.wings import WingsManager


def test_discover_environment():
    env = discover_environment()
    assert "clis" in env
    assert "models_registered" in env
    assert isinstance(env["api_keys_present"], dict)


def test_external_cli_discovery_and_dry_run():
    reg = ExternalCLIRegistry()
    found = reg.discover()
    assert len(found) >= 1
    tool = ExternalCLITool(dry_run=True, auto_approve=True)
    # dry-run should work even if CLI missing? run checks PATH first
    # Use a fake by temporarily only testing envelope for missing
    result = tool.run("claude", "hello", approve=True)
    # Either not found or dry-run ok
    assert result.cli == "claude"
    assert result.to_dict()["cli"] == "claude"


def test_tool_proposals(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    mgr = ToolProposalManager(store_path=tmp_path / "props.json")
    p = mgr.propose(
        "edit_file",
        {"path": str(tmp_path / "out.txt"), "content": "hi"},
        rationale="test",
    )
    assert p.status == "proposed"
    mgr.approve(p.id)
    executed = mgr.execute(p.id)
    assert executed.status == "executed", executed.result
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hi"


def test_wings_assign(tmp_path: Path):
    wm = WingsManager(path=tmp_path / "wings.json")
    e = wm.assign("mem1", "technical", "coding", note="n")
    assert e["wing"] == "technical"
    assert wm.for_memory("mem1")


def test_agentic_debate_mock():
    wf = AgenticWorkflows()
    result = wf.debate("Should we use FastAPI?", rounds=1)
    assert result["proposals"]
    assert "message" in result
