"""Install wizard + postgres setup (dry-run / mock paths only)."""

from pathlib import Path
from unittest.mock import patch

import pytest

from core.install_wizard import run_install_wizard
from core.postgres_setup import (
    detect_postgres,
    setup_database,
    write_dsn_to_config,
)


def test_detect_postgres_shape():
    d = detect_postgres()
    assert "available" in d
    assert "psql" in d
    assert "platform" in d


def test_setup_database_dry_run():
    r = setup_database(live=False)
    assert r.get("ok") is True
    assert r.get("status") == "dry_run"
    assert "dsn_template" in r


def test_write_dsn_to_config(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    dsn = "postgresql+psycopg://superai:secret@localhost:5432/superai"
    r = write_dsn_to_config(dsn, password="secret", persist_password_to_keyring=False)
    assert r.get("ok") is True
    from core.config import Config

    cfg = Config()
    assert cfg.get("memory_dsn") == dsn
    assert cfg.get("memory_backend") == "pgvector"


def test_install_wizard_non_interactive_skip_postgres(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    monkeypatch.setenv("SUPERAI_NON_INTERACTIVE", "1")
    r = run_install_wizard(
        interactive=False,
        skip_postgres=True,
        skip_host_tools=True,
        live=False,
    )
    assert r.get("ok") is True
    assert "initialize" in r.get("steps", [])
    assert "postgres_skipped" in r.get("steps", []) or r.get("postgres", {}).get(
        "skipped"
    )


def test_install_wizard_postgres_dry_run(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / ".superai").mkdir(parents=True)
    r = run_install_wizard(
        interactive=False,
        with_postgres=True,
        skip_host_tools=True,
        live=False,
        yes=False,
    )
    assert r.get("ok") is True
    assert "postgres" in r
    # dry-run should not fail overall
    assert r["postgres"].get("status") in {
        "dry_run",
        "dry_run_missing",
        "ready",
        None,
    } or r["postgres"].get("ok") is not False


def test_ensure_postgres_dry_run_no_side_effects(tmp_path: Path, monkeypatch):
    from core.postgres_setup import ensure_postgres_for_superai

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    r = ensure_postgres_for_superai(live=False, install_if_missing=True)
    assert r.get("live") is False
    assert r.get("ok") is True
