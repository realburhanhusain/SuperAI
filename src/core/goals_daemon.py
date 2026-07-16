"""
N206 — Daemon for goals / schedules.

Production local daemon:
- PID + state files under ~/.superai/daemon/
- start / stop / status / tick / run-loop
- Each tick: schedules run-due + goals heartbeat + optional notify/execute
- Safety: never yolo; execute_goals opt-in; caps on max goals
- Foreground loop or background spawn (subprocess)

CLI:
  superai daemon start|stop|status|tick|run
  superai goals tick  (single tick; existing)
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def daemon_dir() -> Path:
    p = Path.home() / ".superai" / "daemon"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pid_path() -> Path:
    return daemon_dir() / "goals.pid"


def state_path() -> Path:
    return daemon_dir() / "goals_daemon.json"


def log_path() -> Path:
    log_dir = Path.home() / ".superai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "goals_daemon.log"


def default_config() -> Dict[str, Any]:
    return {
        "interval_sec": 60.0,
        "execute_goals": False,
        "notify": True,
        "schedule_due": True,
        "max_goals": 2,
        "max_ticks": 0,  # 0 = infinite
    }


def load_state() -> Dict[str, Any]:
    p = state_path()
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = default_config()
                base.update(data)
                return base
        except Exception:
            pass
    return default_config()


def save_state(updates: Dict[str, Any]) -> Dict[str, Any]:
    st = load_state()
    st.update(updates or {})
    st["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state_path().write_text(json.dumps(st, indent=2), encoding="utf-8")
    return st


def _append_log(line: str) -> None:
    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ')} {line}\n")
    except Exception:
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if sys.platform == "win32":
            # OpenProcess check via tasklist is heavy; use os.kill(pid, 0) may not work on Windows
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, int(pid))
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def read_pid() -> Optional[int]:
    p = pid_path()
    if not p.is_file():
        return None
    try:
        pid = int(p.read_text(encoding="utf-8").strip().split()[0])
        return pid
    except Exception:
        return None


def write_pid(pid: int) -> None:
    pid_path().write_text(str(int(pid)) + "\n", encoding="utf-8")


def clear_pid() -> None:
    try:
        if pid_path().is_file():
            pid_path().unlink()
    except Exception:
        pass


def status() -> Dict[str, Any]:
    """Daemon status for CLI/doctor."""
    from .spend_guard import ensure_public_result

    pid = read_pid()
    alive = _pid_alive(pid) if pid else False
    if pid and not alive:
        clear_pid()
        pid = None
    st = load_state()
    return ensure_public_result(
        {
            "ok": True,
            "running": bool(alive),
            "pid": pid if alive else None,
            "pid_file": str(pid_path()),
            "state_file": str(state_path()),
            "log_file": str(log_path()),
            "config": {
                "interval_sec": st.get("interval_sec"),
                "execute_goals": st.get("execute_goals"),
                "notify": st.get("notify"),
                "schedule_due": st.get("schedule_due"),
                "max_goals": st.get("max_goals"),
                "max_ticks": st.get("max_ticks"),
            },
            "last_tick": st.get("last_tick"),
            "last_tick_result": st.get("last_tick_result"),
            "ticks_total": st.get("ticks_total") or 0,
            "started_at": st.get("started_at"),
            "commands": [
                "superai daemon status",
                "superai daemon start --interval 60",
                "superai daemon tick",
                "superai daemon stop",
            ],
        },
        mock=True,
        ok=True,
    )


def tick(
    *,
    execute_goals: Optional[bool] = None,
    notify: Optional[bool] = None,
    schedule_due: Optional[bool] = None,
    max_goals: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Single daemon tick: schedules + goals heartbeat + optional notify/execute.
    """
    from .assistant_goals import GoalStore
    from .spend_guard import ensure_public_result

    st = load_state()
    ex = bool(st.get("execute_goals") if execute_goals is None else execute_goals)
    nt = bool(st.get("notify") if notify is None else notify)
    sch = bool(st.get("schedule_due") if schedule_due is None else schedule_due)
    mx = int(st.get("max_goals") if max_goals is None else max_goals)

    started = time.time()
    try:
        result = GoalStore().daemon_tick(
            max_goals=mx,
            execute=ex,
            notify=nt,
            schedule_due=sch,
        )
        result["latency_sec"] = round(time.time() - started, 3)
        result["daemon_tick"] = True
        result["execute_goals"] = ex
    except Exception as e:
        result = {
            "ok": False,
            "error": str(e)[:400],
            "daemon_tick": True,
        }

    ticks = int(st.get("ticks_total") or 0) + 1
    save_state(
        {
            "last_tick": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "last_tick_result": {
                "ok": result.get("ok"),
                "due_count": result.get("due_count"),
                "schedule_ran": (result.get("schedule") or {}).get("ran"),
                "executed": (result.get("execute") or {}).get("executed"),
            },
            "ticks_total": ticks,
        }
    )
    _append_log(
        f"tick ok={result.get('ok')} due={result.get('due_count')} "
        f"sched={(result.get('schedule') or {}).get('ran')} exec={ex}"
    )
    return ensure_public_result(result, ok=bool(result.get("ok", True)))


def run_loop(
    *,
    interval_sec: float = 60.0,
    execute_goals: bool = False,
    notify: bool = True,
    schedule_due: bool = True,
    max_goals: int = 2,
    max_ticks: int = 0,
    write_pid_file: bool = True,
) -> Dict[str, Any]:
    """
    Foreground loop: tick → sleep → repeat until max_ticks or signal.
    """
    save_state(
        {
            "interval_sec": float(interval_sec),
            "execute_goals": bool(execute_goals),
            "notify": bool(notify),
            "schedule_due": bool(schedule_due),
            "max_goals": int(max_goals),
            "max_ticks": int(max_ticks),
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "foreground",
        }
    )
    if write_pid_file:
        write_pid(os.getpid())
    _append_log(
        f"loop start interval={interval_sec} execute={execute_goals} max_ticks={max_ticks}"
    )

    stop = {"flag": False}

    def _handle(sig, frame):  # noqa: ARG001
        stop["flag"] = True
        _append_log(f"signal {sig} stop")

    try:
        signal.signal(signal.SIGINT, _handle)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _handle)
    except Exception:
        pass

    n = 0
    last: Dict[str, Any] = {}
    try:
        while not stop["flag"]:
            last = tick(
                execute_goals=execute_goals,
                notify=notify,
                schedule_due=schedule_due,
                max_goals=max_goals,
            )
            n += 1
            if max_ticks and n >= max_ticks:
                break
            # interruptible sleep
            end = time.time() + max(1.0, float(interval_sec))
            while time.time() < end and not stop["flag"]:
                time.sleep(min(0.5, end - time.time()))
    finally:
        if write_pid_file and read_pid() == os.getpid():
            clear_pid()
        save_state({"mode": "stopped", "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        _append_log(f"loop end ticks={n}")

    return {
        "ok": True,
        "ticks": n,
        "last": last,
        "stopped": True,
    }


def start_background(
    *,
    interval_sec: float = 60.0,
    execute_goals: bool = False,
    notify: bool = True,
    schedule_due: bool = True,
    max_goals: int = 2,
    max_ticks: int = 0,
) -> Dict[str, Any]:
    """
    Spawn background daemon process: python -m core.goals_daemon_main ...
    """
    from .spend_guard import ensure_public_result

    cur = status()
    if cur.get("running"):
        return ensure_public_result(
            {
                "ok": True,
                "already_running": True,
                "pid": cur.get("pid"),
                "message": "daemon already running",
            },
            ok=True,
        )

    save_state(
        {
            "interval_sec": float(interval_sec),
            "execute_goals": bool(execute_goals),
            "notify": bool(notify),
            "schedule_due": bool(schedule_due),
            "max_goals": int(max_goals),
            "max_ticks": int(max_ticks),
            "mode": "starting",
        }
    )

    # Prefer `superai daemon run` if on PATH; else python -m
    args = [
        sys.executable,
        "-c",
        (
            "from core.goals_daemon import run_loop; "
            f"run_loop(interval_sec={float(interval_sec)!r}, "
            f"execute_goals={bool(execute_goals)!r}, notify={bool(notify)!r}, "
            f"schedule_due={bool(schedule_due)!r}, max_goals={int(max_goals)!r}, "
            f"max_ticks={int(max_ticks)!r}, write_pid_file=True)"
        ),
    ]
    env = os.environ.copy()
    # Ensure src on path for -c import
    src = str(Path(__file__).resolve().parents[1])
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")

    logf = open(log_path(), "a", encoding="utf-8")
    try:
        creationflags = 0
        if sys.platform == "win32":
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            creationflags = 0x00000008 | 0x00000200
        proc = subprocess.Popen(
            args,
            stdout=logf,
            stderr=logf,
            stdin=subprocess.DEVNULL,
            env=env,
            cwd=str(Path.cwd()),
            creationflags=creationflags,
            close_fds=sys.platform != "win32",
        )
    except Exception as e:
        logf.close()
        return ensure_public_result(
            {"ok": False, "error": f"spawn_failed:{e}"[:300]}, ok=False
        )

    write_pid(proc.pid)
    save_state(
        {
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "mode": "background",
            "pid": proc.pid,
        }
    )
    _append_log(f"start background pid={proc.pid}")
    # give process a moment
    time.sleep(0.3)
    alive = _pid_alive(proc.pid)
    return ensure_public_result(
        {
            "ok": True,
            "started": True,
            "pid": proc.pid,
            "running": alive,
            "log_file": str(log_path()),
            "interval_sec": interval_sec,
            "execute_goals": execute_goals,
        },
        ok=True,
    )


def stop() -> Dict[str, Any]:
    """Stop background daemon via PID."""
    from .spend_guard import ensure_public_result

    pid = read_pid()
    if not pid:
        return ensure_public_result(
            {"ok": True, "stopped": False, "message": "not_running"}, ok=True
        )
    alive = _pid_alive(pid)
    if not alive:
        clear_pid()
        save_state({"mode": "stopped"})
        return ensure_public_result(
            {"ok": True, "stopped": True, "message": "stale_pid_cleared", "pid": pid},
            ok=True,
        )
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=15,
            )
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.5)
            if _pid_alive(pid):
                os.kill(pid, signal.SIGKILL)
    except Exception as e:
        return ensure_public_result(
            {"ok": False, "error": str(e)[:300], "pid": pid}, ok=False
        )
    clear_pid()
    save_state(
        {
            "mode": "stopped",
            "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    _append_log(f"stop pid={pid}")
    return ensure_public_result(
        {"ok": True, "stopped": True, "pid": pid}, ok=True
    )
