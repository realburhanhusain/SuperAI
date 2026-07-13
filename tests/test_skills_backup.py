"""Phase 4–5 skills + backup tests."""

from pathlib import Path

from core.backup_manager import BackupManager
from core.skills import SkillsManager


def test_skill_create_relevance_and_prompt(tmp_path: Path):
    sm = SkillsManager(skills_dir=str(tmp_path / "skills"))
    sm.create_skill(
        name="FastAPI Patterns",
        content="Use APIRouter and lifespan for FastAPI apps.",
        tags=["coding", "fastapi", "python"],
        description="FastAPI coding patterns",
    )
    relevant = sm.get_relevant_skills("Create a FastAPI hello world", top_k=3)
    assert relevant
    assert relevant[0]["name"] == "FastAPI Patterns"
    assert "FastAPI" in (relevant[0].get("content") or "") or "APIRouter" in (
        relevant[0].get("content") or ""
    )
    block = sm.format_for_prompt(relevant)
    assert "Skill: FastAPI Patterns" in block
    sm.mark_used("FastAPI Patterns")
    listed = sm.list_skills()
    assert listed[0]["usage_count"] == 1


def test_backup_create_verify_restore(tmp_path: Path):
    home = tmp_path / ".superai"
    home.mkdir()
    (home / "config.json").write_text('{"mock_mode": true}', encoding="utf-8")
    hist = home / "history"
    hist.mkdir()
    (hist / "t1.json").write_text('{"task_id": "t1"}', encoding="utf-8")
    skills = home / "skills"
    skills.mkdir()
    (skills / "demo.md").write_text("# skill", encoding="utf-8")

    key = b"0" * 32
    bm = BackupManager(
        backup_dir=str(home / "backups"),
        encryption_key=key,
        superai_home=str(home),
        key_file=str(home / ".backup_key"),
    )
    # Write key file consistently
    Path(home / ".backup_key").write_bytes(key)

    path = bm.create_backup(force_full=True)
    assert path
    assert Path(path).exists()

    verify = bm.verify_backup(path)
    assert verify.get("ok") is True
    assert verify.get("member_count", 0) >= 1

    restore_dir = tmp_path / "restored"
    result = bm.restore_backup(path, restore_dir=str(restore_dir))
    assert result.get("ok") is True
    # config.json should appear under restore tree
    found = list(restore_dir.rglob("config.json"))
    assert found, f"config.json not in restore tree: {list(restore_dir.rglob('*'))}"


def test_backup_incremental_noop(tmp_path: Path):
    home = tmp_path / ".superai"
    home.mkdir()
    (home / "config.json").write_text("{}", encoding="utf-8")
    key = b"1" * 32
    bm = BackupManager(
        backup_dir=str(home / "backups"),
        encryption_key=key,
        superai_home=str(home),
        key_file=str(home / ".backup_key"),
    )
    Path(home / ".backup_key").write_bytes(key)
    p1 = bm.create_backup(force_full=True)
    assert p1
    p2 = bm.create_backup(incremental=True)
    # No changes → empty string
    assert p2 == ""
