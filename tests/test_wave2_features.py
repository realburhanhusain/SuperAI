"""Wave-2 features M9-N30 smoke tests."""

from pathlib import Path

from core.ab_routing import ABRouter
from core.approval_tui import prompt_approval
from core.compliance import enable_compliance_mode, compliance_status
from core.context_manager import summarize_text, trim_messages
from core.cost_forecast import forecast_task_cost
from core.diagnostics import build_diagnostics_bundle
from core.diff_edit import unified_diff, apply_edit_with_diff
from core.i18n import t
from core.keyring_store import SecretStore
from core.langgraph_export import plan_to_langgraph
from core.memory_gdpr import forget_query
from core.onboarding import run_onboarding
from core.output_validate import extract_json, validate_json_schema_simple
from core.profile_bundle import export_profile, import_profile
from core.rate_queue import RateLimitQueue
from core.skill_permissions import SkillPermissions
from core.tdd_loop import detect_test_command, run_tests
from core.telemetry import Telemetry
from core.version_check import check_update, _is_newer
from core.workspace_index import build_index, search_index


def test_secrets_store(tmp_path: Path):
    s = SecretStore(fallback_dir=tmp_path / "sec")
    s.set("DEMO_KEY", "secret123456")
    assert s.get("DEMO_KEY") == "secret123456"
    assert s.delete("DEMO_KEY")


def test_approval_force():
    assert prompt_approval("t", force=True) is True
    assert prompt_approval("t", force=False) is False


def test_rate_queue(tmp_path: Path):
    q = RateLimitQueue(path=tmp_path / "q.json")
    item = q.enqueue("call", {"x": 1}, error="429")
    assert item["id"]
    assert q.list_items()


def test_diagnostics(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    path = build_diagnostics_bundle(tmp_path / "d.zip")
    assert path.exists()


def test_version_check():
    r = check_update()
    assert "local" in r
    assert _is_newer("0.2.0", "0.1.0")


def test_diff_edit(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    f = tmp_path / "a.txt"
    f.write_text("hello\n", encoding="utf-8")
    d = unified_diff("hello\n", "hello world\n", "a.txt")
    assert "hello world" in d
    r = apply_edit_with_diff(f, "hello world\n", auto_approve=True, show=False)
    assert r["ok"] and r["changed"]
    assert f.read_text(encoding="utf-8") == "hello world\n"


def test_tdd_detect():
    cmd = detect_test_command(Path.cwd())
    assert isinstance(cmd, list) and cmd


def test_context_trim():
    msgs = [
        {"role": "system", "content": "sys"},
        *[{"role": "user", "content": "x" * 100} for _ in range(50)],
    ]
    trimmed = trim_messages(msgs, max_tokens=200)
    assert any(m["role"] == "system" for m in trimmed)
    assert len(trimmed) < len(msgs)
    assert "summarized" in summarize_text("a" * 5000, max_chars=100) or len(
        summarize_text("a" * 5000, max_chars=100)
    ) <= 200


def test_workspace_index(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_WORKSPACE", str(tmp_path))
    (tmp_path / "mod.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    idx = build_index(tmp_path)
    assert idx["file_count"] >= 1
    hits = search_index("hello", idx)
    assert hits


def test_validate_json():
    data = extract_json('```json\n{"a": 1}\n```')
    assert data == {"a": 1}
    assert validate_json_schema_simple(data, ["a"])["ok"]


def test_profile_bundle(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    home = tmp_path / ".superai"
    home.mkdir()
    (home / "config.json").write_text('{"mock_mode": true}', encoding="utf-8")
    z = export_profile(tmp_path / "p.zip")
    assert z.exists()
    r = import_profile(z, dry_run=True)
    assert r["ok"]


def test_compliance(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    enable_compliance_mode()
    st = compliance_status()
    assert st.get("compliance_mode") or st.get("mock_mode") is not None


def test_forecast():
    f = forecast_task_cost("build a small API")
    assert f["steps"] >= 1
    assert "estimated_usd" in f


def test_ab_and_skills_perm(tmp_path: Path):
    ab = ABRouter(path=tmp_path / "ab.json")
    ab.create("exp1", "gpt-4o", "grok-3", traffic_b_pct=50)
    m = ab.pick("coding")
    assert m in {"gpt-4o", "grok-3"}
    sp = SkillPermissions(path=tmp_path / "sp.json")
    sp.set_tools("demo", ["web_search"])
    assert sp.allowed("demo", "web_search")
    assert not sp.allowed("demo", "run_shell")


def test_langgraph_and_i18n():
    g = plan_to_langgraph("build something")
    assert g["nodes"] and g["edges"]
    assert t("ready")


def test_onboarding_and_telemetry(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    r = run_onboarding()
    assert r["ok"]
    tel = Telemetry(path=tmp_path / "t.jsonl")
    tel.enable()
    tel.event("run_task", {"success": True, "status": "success"})
    assert tel.is_enabled()
    tel.disable()


def test_memory_forget(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SUPERAI_EMBEDDING_HASH", "1")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    from core.memory_palace import MemoryPalace

    mp = MemoryPalace()  # uses ~/.superai/memory under patched home
    mp.store("unique-forget-token-xyz", tags=["t"])
    r = forget_query("unique-forget-token-xyz", dry_run=True)
    assert r["matched"] >= 1
