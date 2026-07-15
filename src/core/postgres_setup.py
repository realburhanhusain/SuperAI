"""
Optional Postgres + pgvector setup for SuperAI Memory Palace.

Opt-in during interactive install/onboard:
  - detect existing PostgreSQL (service / psql on PATH / Program Files)
  - optionally install via winget / brew / apt (never silent without consent)
  - create database + role + CREATE EXTENSION vector
  - write DSN into SuperAI config (memory_dsn)

Safety: no install runs unless live=True (user confirmed or --yes).
"""

from __future__ import annotations

import os
import platform
import secrets
import shutil
import string
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


DEFAULT_DB = "superai"
DEFAULT_USER = "superai"
DEFAULT_PORT = 5432


def _run(
    argv: Sequence[str],
    *,
    timeout: float = 120.0,
    env: Optional[Dict[str, str]] = None,
    input_text: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            env=env,
            input=input_text,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[-4000:],
            "stderr": (proc.stderr or "")[-2000:],
            "command": list(argv),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e), "command": list(argv)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s", "command": list(argv)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e), "command": list(argv)}


def _which_psql() -> Optional[str]:
    w = shutil.which("psql") or shutil.which("psql.exe")
    if w:
        return w
    # Windows default install paths
    if platform.system().lower().startswith("win"):
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
        if base.is_dir():
            versions = sorted(
                [p for p in base.iterdir() if p.is_dir()],
                key=lambda p: p.name,
                reverse=True,
            )
            for ver in versions:
                cand = ver / "bin" / "psql.exe"
                if cand.is_file():
                    return str(cand)
    return None


def _which_pg_isready() -> Optional[str]:
    w = shutil.which("pg_isready") or shutil.which("pg_isready.exe")
    if w:
        return w
    psql = _which_psql()
    if psql:
        cand = Path(psql).with_name(
            "pg_isready.exe" if platform.system().lower().startswith("win") else "pg_isready"
        )
        if cand.is_file():
            return str(cand)
    return None


def detect_postgres() -> Dict[str, Any]:
    """Probe local PostgreSQL availability (no install)."""
    psql = _which_psql()
    pg_isready = _which_pg_isready()
    version = None
    ready = False
    service_running = False

    if psql:
        r = _run([psql, "--version"], timeout=15)
        if r.get("ok"):
            version = (r.get("stdout") or "").strip().split("\n")[0]

    if pg_isready:
        r = _run([pg_isready, "-h", "localhost", "-p", str(DEFAULT_PORT)], timeout=10)
        ready = bool(r.get("ok"))

    if platform.system().lower().startswith("win"):
        r = _run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Service -Name '*postgres*' -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Status"],
            timeout=20,
        )
        out = (r.get("stdout") or "").lower()
        service_running = "running" in out
        if service_running and not ready:
            # service up but pg_isready may fail without path — treat as present
            ready = True

    return {
        "psql": psql,
        "pg_isready": pg_isready,
        "version": version,
        "ready": ready,
        "service_running": service_running,
        "available": bool(psql) or service_running,
        "platform": platform.system(),
    }


def _install_argv() -> Optional[List[str]]:
    system = platform.system().lower()
    if system.startswith("win"):
        if shutil.which("winget"):
            # Official PostgreSQL winget package family
            return [
                "winget",
                "install",
                "-e",
                "--id",
                "PostgreSQL.PostgreSQL.17",
                "--accept-package-agreements",
                "--accept-source-agreements",
            ]
        if shutil.which("choco"):
            return ["choco", "install", "postgresql", "-y"]
    if system == "darwin" and shutil.which("brew"):
        return ["brew", "install", "postgresql@17"]
    if system == "linux":
        if shutil.which("apt-get") or shutil.which("apt"):
            apt = "apt-get" if shutil.which("apt-get") else "apt"
            return ["sudo", apt, "install", "-y", "postgresql", "postgresql-contrib"]
    return None


def install_postgres_server(*, live: bool = False, timeout: float = 900.0) -> Dict[str, Any]:
    """
    Install PostgreSQL server via host package manager.
    dry-run when live=False.
    """
    argv = _install_argv()
    if not argv:
        return {
            "ok": False,
            "status": "no_recipe",
            "hint": (
                "Install PostgreSQL manually, then re-run. "
                "Windows: winget install PostgreSQL.PostgreSQL.17 · "
                "macOS: brew install postgresql@17 · "
                "Linux: apt install postgresql postgresql-contrib. "
                "Also install the pgvector extension for your major version."
            ),
            "url": "https://www.postgresql.org/download/",
        }
    if not live:
        return {"ok": True, "status": "dry_run", "command": argv, "command_str": " ".join(argv)}

    r = _run(argv, timeout=timeout)
    # Re-detect after install
    time.sleep(2)
    det = detect_postgres()
    return {
        "ok": bool(r.get("ok")) or det.get("available"),
        "status": "installed" if (r.get("ok") or det.get("available")) else "failed",
        "install": r,
        "detect_after": det,
        "notes": (
            "If psql is not on PATH, open a new terminal or add PostgreSQL\\bin to PATH."
        ),
    }


def _gen_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _psql_env(password: Optional[str] = None) -> Dict[str, str]:
    env = os.environ.copy()
    # Avoid interactive password prompts when PGPASSWORD is set
    if password:
        env["PGPASSWORD"] = password
    return env


def _psql_base(
    psql: str,
    *,
    host: str = "localhost",
    port: int = DEFAULT_PORT,
    user: str = "postgres",
    dbname: str = "postgres",
) -> List[str]:
    return [
        psql,
        "-h",
        host,
        "-p",
        str(port),
        "-U",
        user,
        "-d",
        dbname,
        "-v",
        "ON_ERROR_STOP=1",
    ]


def setup_database(
    *,
    host: str = "localhost",
    port: int = DEFAULT_PORT,
    admin_user: str = "postgres",
    admin_password: Optional[str] = None,
    db_name: str = DEFAULT_DB,
    db_user: str = DEFAULT_USER,
    db_password: Optional[str] = None,
    live: bool = False,
) -> Dict[str, Any]:
    """
    Create role + database + vector extension. Returns DSN on success.
    """
    psql = _which_psql()
    if not psql:
        return {
            "ok": False,
            "error": "psql not found on PATH or under Program Files/PostgreSQL",
            "hint": "Install PostgreSQL or add bin/ to PATH, then retry.",
        }

    password = db_password or _gen_password()
    admin_pw = admin_password or os.getenv("PGPASSWORD") or os.getenv("SUPERAI_PG_ADMIN_PASSWORD")
    env = _psql_env(admin_pw)

    steps: List[Dict[str, Any]] = []
    sql_cmds = [
        (
            "create_role",
            f"DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{db_user}') THEN "
            f"CREATE ROLE {db_user} LOGIN PASSWORD '{password}'; "
            f"END IF; END $$;",
        ),
        (
            "create_db",
            f"SELECT 'exists' FROM pg_database WHERE datname = '{db_name}';",
        ),
    ]

    if not live:
        dsn = (
            f"postgresql+psycopg://{db_user}:***@{host}:{port}/{db_name}"
        )
        return {
            "ok": True,
            "status": "dry_run",
            "psql": psql,
            "db_name": db_name,
            "db_user": db_user,
            "dsn_template": dsn,
            "steps_planned": ["create_role", "create_database", "grant", "create_extension_vector"],
            "notes": "Pass live=True after reviewing. Password will be generated and saved to config.",
        }

    # create role
    base = _psql_base(psql, host=host, port=port, user=admin_user, dbname="postgres")
    r_role = _run(
        [*base, "-c", sql_cmds[0][1]],
        env=env,
        timeout=60,
    )
    steps.append({"step": "create_role", **r_role})

    # create database if missing
    r_exists = _run(
        [*base, "-tAc", f"SELECT 1 FROM pg_database WHERE datname='{db_name}'"],
        env=env,
        timeout=30,
    )
    exists = (r_exists.get("stdout") or "").strip() == "1"
    steps.append({"step": "check_db", **r_exists, "exists": exists})
    if not exists:
        r_db = _run(
            [*base, "-c", f"CREATE DATABASE {db_name} OWNER {db_user};"],
            env=env,
            timeout=60,
        )
        steps.append({"step": "create_database", **r_db})
        if not r_db.get("ok"):
            return {
                "ok": False,
                "error": "failed to create database",
                "steps": steps,
                "hint": "Check admin credentials (PGPASSWORD / SUPERAI_PG_ADMIN_PASSWORD).",
            }
    else:
        # ensure ownership/privileges
        r_grant = _run(
            [
                *base,
                "-c",
                f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};",
            ],
            env=env,
            timeout=30,
        )
        steps.append({"step": "grant_db", **r_grant})

    # extension in target DB
    base_db = _psql_base(psql, host=host, port=port, user=admin_user, dbname=db_name)
    r_ext = _run(
        [*base_db, "-c", "CREATE EXTENSION IF NOT EXISTS vector;"],
        env=env,
        timeout=60,
    )
    steps.append({"step": "create_extension_vector", **r_ext})
    vector_ok = bool(r_ext.get("ok"))
    if not vector_ok:
        # try as superuser message
        steps.append(
            {
                "step": "vector_note",
                "ok": False,
                "hint": (
                    "CREATE EXTENSION vector failed. Install pgvector for your "
                    "Postgres major version, then re-run: "
                    "superai install-postgres --setup-only --live"
                ),
            }
        )

    # grants on public schema for app user
    r_sch = _run(
        [
            *base_db,
            "-c",
            f"GRANT ALL ON SCHEMA public TO {db_user}; "
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO {db_user};",
        ],
        env=env,
        timeout=30,
    )
    steps.append({"step": "schema_grants", **r_sch})

    dsn = f"postgresql+psycopg://{db_user}:{password}@{host}:{port}/{db_name}"
    dsn_safe = f"postgresql+psycopg://{db_user}:***@{host}:{port}/{db_name}"

    return {
        "ok": True,
        "status": "configured",
        "psql": psql,
        "db_name": db_name,
        "db_user": db_user,
        "db_password": password,
        "dsn": dsn,
        "dsn_safe": dsn_safe,
        "vector_extension": vector_ok,
        "steps": steps,
        "host": host,
        "port": port,
    }


def write_dsn_to_config(
    dsn: str,
    *,
    password: Optional[str] = None,
    persist_password_to_keyring: bool = True,
) -> Dict[str, Any]:
    """Persist memory_dsn (+ backend) into SuperAI config; optional keyring password."""
    from .config import Config

    cfg = Config()
    cfg.set("memory_backend", "pgvector", persist=False)
    cfg.set("memory_dsn", dsn, persist=True)
    # Also set process env for current session
    os.environ["SUPERAI_MEMORY_DSN"] = dsn
    os.environ["SUPERAI_MEMORY_BACKEND"] = "pgvector"

    keyring_note = None
    if password and persist_password_to_keyring:
        try:
            from .keyring_store import SecretStore

            SecretStore().set("SUPERAI_MEMORY_DB_PASSWORD", password)
            keyring_note = "password stored in keyring as SUPERAI_MEMORY_DB_PASSWORD"
        except Exception as e:  # noqa: BLE001
            keyring_note = f"keyring skip: {e}"

    return {
        "ok": True,
        "config_path": str(cfg.config_path),
        "memory_dsn_set": True,
        "memory_backend": "pgvector",
        "keyring": keyring_note,
    }


def ensure_postgres_for_superai(
    *,
    live: bool = False,
    install_if_missing: bool = True,
    admin_password: Optional[str] = None,
    host: str = "localhost",
    port: int = DEFAULT_PORT,
) -> Dict[str, Any]:
    """
    Full pipeline: detect → optional install → setup DB/extension → write config.
    """
    out: Dict[str, Any] = {"live": live, "steps": []}
    det = detect_postgres()
    out["detect"] = det
    out["steps"].append("detect")

    if not det.get("available") and install_if_missing:
        inst = install_postgres_server(live=live)
        out["install"] = inst
        out["steps"].append("install")
        if live and not inst.get("ok"):
            out["ok"] = False
            out["error"] = "postgres install failed or unavailable"
            return out
        if not live:
            out["ok"] = True
            out["status"] = "dry_run"
            out["next"] = [
                "Re-run with live=True / superai install --with-postgres --yes",
                "Or install Postgres manually, then superai install-postgres --setup-only --live",
            ]
            return out
        det = detect_postgres()
        out["detect_after_install"] = det

    if not det.get("available") and not (out.get("detect_after_install") or {}).get("available"):
        # still missing
        if not live:
            out["ok"] = True
            out["status"] = "dry_run_missing"
            return out
        out["ok"] = False
        out["error"] = "PostgreSQL not available after install attempt"
        return out

    setup = setup_database(
        host=host,
        port=port,
        admin_password=admin_password,
        live=live,
    )
    out["setup"] = {k: v for k, v in setup.items() if k != "db_password"}
    out["steps"].append("setup_database")

    if not live:
        out["ok"] = True
        out["status"] = "dry_run"
        return out

    if not setup.get("ok"):
        out["ok"] = False
        out["error"] = setup.get("error") or "database setup failed"
        return out

    dsn = setup.get("dsn")
    if not dsn:
        out["ok"] = False
        out["error"] = "no DSN produced"
        return out

    written = write_dsn_to_config(
        dsn, password=setup.get("db_password"), persist_password_to_keyring=True
    )
    out["config"] = written
    out["steps"].append("write_config")
    out["ok"] = True
    out["status"] = "ready"
    out["dsn_safe"] = setup.get("dsn_safe")
    out["vector_extension"] = setup.get("vector_extension")
    # Verify store can open
    try:
        from .pgvector_store import PgvectorMemoryStore

        st = PgvectorMemoryStore(dsn=dsn)
        out["store_stats"] = st.stats()
    except Exception as e:  # noqa: BLE001
        out["store_stats_error"] = str(e)
    return out
