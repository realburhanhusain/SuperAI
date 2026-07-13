"""Future-plan gap features: compare, cache, blacklist, skills, backup scopes, etc."""

from pathlib import Path

from superai.core.backup_manager import sources_for_scopes
from superai.core.hitl import HITLStore
from superai.core.load_balancer import LoadBalancingStrategy, parse_strategy
from superai.core.memory_chat import MemoryConversation
from superai.core.model_blacklist import ModelBlacklist
from superai.core.model_compare import benchmark_models, compare_models
from superai.core.model_pinning import ModelPinStore
from superai.core.model_registry import ModelRegistry
from superai.core.notion_stub import NotionClient
from superai.core.skills import SkillsManager
from superai.core.step_cache import StepResultCache
from superai.core.task_planner import TaskPlanner


class _R:
    pass


def test_parse_parallel_voting():
    assert parse_strategy("parallel_voting") == LoadBalancingStrategy.PARALLEL_VOTING


def test_compare_and_benchmark_mock():
    r = compare_models("hello world", models=["gpt-4o", "grok-3"], use_mock=True)
    assert r["count"] >= 1
    assert r["winner"]
    b = benchmark_models(models=["gpt-4o"], use_mock=True)
    assert b["summary"]


def test_step_cache(tmp_path: Path):
    c = StepResultCache(path=tmp_path / "cache.json")
    key = c.put("step desc", {"status": "success", "result": "ok"}, model="m")
    assert key
    hit = c.get("step desc", "m")
    assert hit and hit["status"] == "success"
    c.save_run_checkpoint("t1", "task", [{"step": 1}], [2, 3])
    assert c.get_run("t1")
    assert c.list_runs()


def test_blacklist_auto(tmp_path: Path):
    bl = ModelBlacklist(path=tmp_path / "bl.json")
    bl.data["auto_threshold"] = 3
    for _ in range(3):
        newly = bl.record_failure("bad-model")
    assert bl.is_model_blocked("bad-model")
    bl.unblock_model("bad-model")
    assert not bl.is_model_blocked("bad-model")


def test_skills_crud_deps_validate(tmp_path: Path):
    sm = SkillsManager(skills_dir=str(tmp_path / "skills"))
    sm.create_skill("base", "Base skill content long enough", tags=["base"])
    sm.create_skill("child", "Child skill content long enough", tags=["child"])
    sm.set_dependencies("child", ["base"])
    order = sm.resolve_dependencies("child")
    assert order[0] == "base"
    v = sm.validate_skill("child")
    assert v["ok"] is True
    sm.improve_skill("child", "more tips")
    assert sm.delete_skill("child")


def test_backup_scopes(tmp_path: Path):
    paths = sources_for_scopes(["memory", "skills"], home=tmp_path)
    assert any(p.name == "memory" for p in paths)
    assert any(p.name == "skills" for p in paths)
    full = sources_for_scopes(["full"], home=tmp_path)
    assert len(full) >= 5


def test_plan_export():
    p = TaskPlanner(_R())
    data = p.export_plan("build a service")
    assert data["steps"]
    md = p.export_plan_markdown("build a service")
    assert "Step" in md


def test_pins(tmp_path: Path):
    store = ModelPinStore(path=tmp_path / "pins.json")
    store.pin("gpt-4o", model_id="gpt-4o-2024-08-06", note="stable")
    assert store.get("gpt-4o")["model_id"].startswith("gpt-4o")
    reg = ModelRegistry()
    n = store.apply_to_registry(reg)
    assert n >= 0
    store.unpin("gpt-4o")


def test_cli_as_models():
    reg = ModelRegistry()
    added = reg.register_external_clis_as_models()
    assert any(a.startswith("cli:") for a in added)
    assert reg.get_model(added[0]) is not None


def test_memory_chat(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    mc = MemoryConversation(path=tmp_path / "mc.json")
    cid = mc.start()
    r = mc.ask(cid, "anything about fastapi")
    assert r["conversation_id"] == cid
    assert "turn" in r


def test_notion_dry():
    client = NotionClient(dry_run=True)
    assert client.write_page("T", "body")["ok"]
    assert client.search("x")["ok"]


def test_hitl(tmp_path: Path):
    h = HITLStore(path=tmp_path / "hitl.json")
    c = h.request_clarification("tid", "what next?")
    assert c["status"] == "open"
    h.answer_clarification(c["id"], "do A")
    h.veto("tid", "stop")
    assert h.is_vetoed("tid")
