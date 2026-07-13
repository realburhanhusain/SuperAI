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
