"""Depth finishes for previously thin layers."""

from pathlib import Path

from core.agentic import AgenticWorkflows
from core.council import Council
from core.hierarchy import HierarchicalDelegator
from core.hitl import HITLStore
from core.memory_palace import MemoryPalace
from core.model_caller import ModelCaller
from core.model_registry import ModelRegistry
from core.pattern_extract import PatternExtractor
from core.step_cache import StepResultCache
from core.task_planner import TaskPlanner
from core.tool_proposals import ToolProposalManager


def test_planner_heuristic_roles():
    p = TaskPlanner(None)
    steps = p.create_plan("build a payment API", use_llm=False)
    assert len(steps) >= 5
    assert any(getattr(s, "role", None) == "supervisor" for s in steps)
    assert any(s.can_run_parallel for s in steps)


def test_hierarchy_decompose_and_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "true")
    from core.config import Config

    cfg = Config(config_path=str(tmp_path / "c.json"))
    cfg.set("mock_mode", True)
    cfg.set("backup_enabled", False)
    cfg.set("max_delegation_depth", 2)
    tree = HierarchicalDelegator(config=cfg).run("build a tiny CLI tool")
    assert "goal" in tree
    assert tree.get("leaf") is False or tree.get("result")


def test_external_cli_model_call(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    reg = ModelRegistry()
    reg.register_external_clis_as_models()
    caller = ModelCaller(use_mock=True, registry=reg)
    # pick first cli:* model
    names = [n for n in reg.list_all_models() if n.startswith("cli:")]
    assert names
    out = caller.call(model=names[0], prompt="say hi")
    assert out.get("provider") == "external_cli"
    assert out.get("response")


def test_memory_cluster(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    mp = MemoryPalace(persist_directory=str(tmp_path / "mem"))
    mp.store("fastapi routing tips", tags=["coding"], metadata={"task_type": "coding"})
    mp.store("auth jwt patterns", tags=["coding"], metadata={"task_type": "coding"})
    mp.store("market research notes", tags=["research"], metadata={"task_type": "research"})
    clusters = mp.cluster_memories()
    assert clusters
    assert any(c["size"] >= 1 for c in clusters)


def test_council_documents(tmp_path: Path):
    doc = tmp_path / "spec.md"
    doc.write_text("# Spec\nRequire OAuth2.", encoding="utf-8")
    reg = ModelRegistry()
    c = Council(
        caller=ModelCaller(use_mock=True, registry=reg),
        registry=reg,
        voting_mode="majority",
    )
    r = c.run("Choose auth approach", document_paths=[str(doc)])
    assert r.get("documents_injected") is True
    assert r.get("stage0")
    assert r.get("decision")


def test_pattern_extract(tmp_path: Path):
    hist = tmp_path / "learning_history.json"
    hist.write_text(
        __import__("json").dumps(
            [
                {
                    "task_type": "coding",
                    "model_used": "gpt-4o",
                    "success": True,
                    "task_description": "build api endpoint",
                },
                {
                    "task_type": "coding",
                    "model_used": "gpt-4o",
                    "success": True,
                    "task_description": "build service",
                },
            ]
        ),
        encoding="utf-8",
    )
    pe = PatternExtractor(history_path=hist)
    data = pe.extract(min_support=2)
    assert data["type_patterns"]


def test_web_search_proposal_wired():
    from core.tool_proposals import ToolProposalManager

    # Use whatever class name exists
    mgr = ToolProposalManager() if "ToolProposalManager" in dir() else None
    # Directly call private method via instance if available
    if mgr is None:
        import core.tool_proposals as tp

        # find executor class
        for name in dir(tp):
            obj = getattr(tp, name)
            if hasattr(obj, "_exec_web_search_stub"):
                inst = obj()
                r = inst._exec_web_search_stub({"query": "superai"})
                assert "results" in r or r.get("ok") is not None
                return
    else:
        r = mgr._exec_web_search_stub({"query": "superai"})
        assert "results" in r or "query" in r


def test_dynamic_roles():
    r = AgenticWorkflows().dynamic_roles("design a cache layer")
    assert r.get("final")
    assert r["roles"]["supervisor"]


def test_resume_checkpoint(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "true")
    from core.config import Config
    from core.orchestrator import SuperAIOrchestrator

    cfg = Config(config_path=str(tmp_path / "cfg.json"))
    cfg.set("mock_mode", True)
    cfg.set("backup_enabled", False)
    orch = SuperAIOrchestrator(config=cfg)
    # partial checkpoint
    tid = "resume-test-1"
    StepResultCache(path=tmp_path / ".superai" / "step_cache.json").save_run_checkpoint(
        tid,
        "build a demo",
        completed_steps=[
            {
                "step": 1,
                "description": "done",
                "status": "success",
                "result": "ok",
            }
        ],
        remaining_step_ids=[2, 3],
    )
    # re-home step cache path via monkeypatch home
    result = orch.run_task("build a demo", resume_task_id=tid)
    assert result.get("task_id") == tid
