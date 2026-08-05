"""Config system tests (Phase 1)."""

from pathlib import Path

from core.config import Config


def test_initialize_creates_dirs(tmp_path: Path, monkeypatch):
    home = tmp_path / ".superai"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    cfg = Config(config_path=str(home / "config.json"))
    dirs = cfg.initialize()

    assert dirs["home"] == home
    assert (home / "logs").is_dir()
    assert (home / "history").is_dir()
    assert (home / "memory").is_dir()
    assert (home / "skills").is_dir()
    assert (home / "backups").is_dir()
    assert Path(cfg.config_path).is_file()


def test_set_get_persist(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = tmp_path / ".superai" / "config.json"
    path.parent.mkdir(parents=True)

    cfg = Config(config_path=str(path))
    cfg.set("mock_mode", False, persist=True)
    cfg.set("log_level", "DEBUG", persist=True)

    cfg2 = Config(config_path=str(path))
    assert cfg2.get("mock_mode") is False
    assert cfg2.get("log_level") == "DEBUG"


def test_env_override(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = tmp_path / ".superai" / "config.json"
    path.parent.mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_MOCK_MODE", "false")
    monkeypatch.setenv("SUPERAI_LOG_LEVEL", "WARNING")

    cfg = Config(config_path=str(path))
    assert cfg.use_mock is False
    assert cfg.get("log_level") == "WARNING"


def test_save_atomic_crash(tmp_path: Path, monkeypatch):
    import os
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = tmp_path / ".superai" / "config.json"
    path.parent.mkdir(parents=True)
    
    cfg = Config(config_path=str(path))
    cfg.set("mock_mode", False, persist=True)
    
    original_bytes = path.read_bytes()
    
    def mock_replace(*args, **kwargs):
        raise RuntimeError("Simulated crash")
        
    monkeypatch.setattr(os, "replace", mock_replace)
    
    cfg.set("log_level", "CRITICAL", persist=False)
    try:
        cfg.save()
    except RuntimeError:
        pass
        
    assert path.read_bytes() == original_bytes


def test_save_backup_retention(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = tmp_path / ".superai" / "config.json"
    path.parent.mkdir(parents=True)
    
    cfg = Config(config_path=str(path))
    cfg.initialize()
    
    backups_dir = tmp_path / ".superai" / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    for i in range(25):
        (backups_dir / f"config-20260101T0000{i:02d}Z.json").write_text("{}")
        
    cfg.save()
    
    backups = list(backups_dir.glob("config-*.json"))
    assert len(backups) == 20 

