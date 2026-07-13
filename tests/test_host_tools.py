"""Host tools checklist + dry-run install (not bundled)."""

from pathlib import Path

from core.host_tools import (
    HOST_TOOL_CATALOG,
    checklist,
    install_tools,
    list_catalog,
    maybe_auto_install_on_setup,
)
from core.doctor import run_doctor
from core.onboarding import run_onboarding


def test_catalog_has_key_tools():
    ids = {t.id for t in HOST_TOOL_CATALOG}
    for need in ("git", "gh", "aws", "az", "gcloud", "claude", "aider", "gemini", "codex"):
        assert need in ids


def test_checklist_structure(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    report = checklist(profile="core")
    assert report["bundled_in_superai"] is False
    assert report["totals"]["checked"] >= 1
    assert "package_managers" in report
    assert "tools" in report
    # each tool has install_hint
    for t in report["tools"]:
        assert "install_hint" in t
        assert "available" in t


def test_install_dry_run_core(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    report = install_tools(profile="core", dry_run=True, only_missing=True)
    assert report["dry_run"] is True
    assert report["totals"]["attempted"] >= 1
    # statuses should not include live installed
    for r in report["results"]:
        assert r.get("status") in {
            "already_present",
            "dry_run",
            "manual_only",
            "no_recipe",
        }


def test_install_specific_tool_dry_run(monkeypatch):
    # Force git "missing" so we get a dry_run command
    import core.host_tools as ht

    monkeypatch.setattr(ht, "_which_any", lambda names: None)
    report = install_tools(tool_ids=["git"], dry_run=True, only_missing=True)
    assert any(r.get("id") == "git" for r in report["results"])
    git_r = next(r for r in report["results"] if r.get("id") == "git")
    assert git_r.get("status") in {"dry_run", "no_recipe", "manual_only"}


def test_manual_only_not_auto(monkeypatch):
    import core.host_tools as ht

    monkeypatch.setattr(ht, "_which_any", lambda names: None)
    report = install_tools(tool_ids=["cursor", "antigravity"], dry_run=False)
    for r in report["results"]:
        assert r.get("status") == "manual_only"


def test_profiles_filter():
    core = list_catalog(profile="core")
    agentic = list_catalog(profile="agentic")
    cloud = list_catalog(profile="cloud")
    assert all("core" in t.profiles for t in core)
    assert any(t.id == "claude" for t in agentic)
    assert any(t.id == "aws" for t in cloud)
    assert not any(t.id == "aws" for t in core)


def test_doctor_includes_host_tools(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir()
    report = run_doctor(quick=True)
    names = [c["name"] for c in report.get("checks") or []]
    assert "host_tools" in names
    assert report.get("host_tools") is not None


def test_auto_env_dry_run(monkeypatch):
    monkeypatch.setenv("SUPERAI_AUTO_HOST_TOOLS", "1")
    r = maybe_auto_install_on_setup()
    assert r is not None
    assert r.get("dry_run") is True


def test_auto_env_off(monkeypatch):
    monkeypatch.delenv("SUPERAI_AUTO_HOST_TOOLS", raising=False)
    assert maybe_auto_install_on_setup() is None


def test_onboarding_host_tools(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SUPERAI_AUTO_HOST_TOOLS", raising=False)
    r = run_onboarding(non_interactive=True)
    assert "host_tools_check" in r.get("steps") or r.get("host_tools") is not None
