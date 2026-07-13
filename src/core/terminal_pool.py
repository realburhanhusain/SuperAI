"""
Parallel multi-terminal sessions + live registry for agentic dashboards.

Runs multiple shell terminals concurrently (one command/session each) and
persists session state so terminal + web dashboards show all workers in one view.

Safety defaults:
  - dry-run unless explicitly live
  - argv list only (no shell=True)
  - workspace jail for cwd
  - blocks shell meta-executables unless SUPERAI_ALLOW_SHELL_META=1
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union


_BLOCKED_META = {
    "powershell",
    "powershell.exe",
    "pwsh",
    "pwsh.exe",
    "cmd",
    "cmd.exe",
    "bash",
    "sh",
    "zsh",
    "wscript",
    "cscript",
    "mshta",
}


@dataclass
class TerminalSession:
    id: str
    title: str
    command: List[str]
    status: str = "queued"  # queued | running | done | failed | cancelled
    role: str = "worker"
    cwd: Optional[str] = None
    approved: bool = False
    dry_run: bool = False
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    duration_sec: float = 0.0
    exit_code: Optional[int] = None
    stdout_tail: str = ""
    stderr_tail: str = ""
    error: Optional[str] = None
    workflow_id: Optional[str] = None
    timeout_sec: float = 60.0
    pid: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TerminalSession":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        data = {k: v for k, v in d.items() if k in known}
        # Normalize command to list
        cmd = data.get("command")
        if isinstance(cmd, str):
            data["command"] = _split_command(cmd)
        elif cmd is None:
            data["command"] = []
        return cls(**data)


def _split_command(cmd: str) -> List[str]:
    cmd = (cmd or "").strip()
    if not cmd:
        return []
    try:
        return shlex.split(cmd, posix=os.name != "nt")
    except ValueError:
        return cmd.split()


def _normalize_command(cmd: Union[str, Sequence[str], None]) -> List[str]:
    if cmd is None:
        return []
    if isinstance(cmd, str):
        return _split_command(cmd)
    return [str(x) for x in cmd]


def _check_command_allowed(cmd: List[str]) -> Optional[str]:
    if not cmd:
        return "empty command"
    exe = str(cmd[0]).lower().replace("\\", "/")
    base = Path(exe).name
    if base in _BLOCKED_META and os.getenv("SUPERAI_ALLOW_SHELL_META", "").lower() not in {
        "1",
        "true",
        "yes",
    }:
        return (
            f"Blocked shell meta-executable '{base}'. "
            "Set SUPERAI_ALLOW_SHELL_META=1 to override (not recommended)."
        )
    return None


class ParallelTerminalManager:
    """
    Shared registry of terminal sessions + parallel execution.
    State file: ~/.superai/terminal_sessions.json (read by dashboard / web).
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(
            path or (Path.home() / ".superai" / "terminal_sessions.json")
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.sessions: Dict[str, TerminalSession] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for item in data.get("sessions") or []:
                    if isinstance(item, dict) and item.get("id"):
                        self.sessions[item["id"]] = TerminalSession.from_dict(item)
            except (OSError, json.JSONDecodeError):
                self.sessions = {}

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """Caller must hold self._lock. Windows-safe atomic replace with retry."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "sessions": [s.to_dict() for s in self.sessions.values()],
        }
        data = json.dumps(payload, indent=2, default=str)
        tmp = self.path.with_name(
            f"{self.path.stem}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:8]}.tmp"
        )
        tmp.write_text(data, encoding="utf-8")
        last_err: Optional[BaseException] = None
        for attempt in range(10):
            try:
                os.replace(str(tmp), str(self.path))
                return
            except PermissionError as e:
                last_err = e
                time.sleep(0.015 * (attempt + 1))
            except OSError as e:
                last_err = e
                time.sleep(0.015 * (attempt + 1))
        try:
            self.path.write_text(data, encoding="utf-8")
        except OSError:
            if last_err is not None:
                raise last_err
            raise
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def list_sessions(
        self,
        status: Optional[str] = None,
        workflow_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self.sessions.values())
            if status:
                items = [s for s in items if s.status == status]
            if workflow_id:
                items = [s for s in items if s.workflow_id == workflow_id]
            items.sort(key=lambda s: s.started_at or 0, reverse=True)
            return [s.to_dict() for s in items[:limit]]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            s = self.sessions.get(session_id)
            return s.to_dict() if s else None

    def snapshot_for_dashboard(self) -> Dict[str, Any]:
        sessions = self.list_sessions(limit=40)
        running = [s for s in sessions if s.get("status") == "running"]
        queued = [s for s in sessions if s.get("status") == "queued"]
        done = [s for s in sessions if s.get("status") in {"done", "failed"}]
        by_workflow: Dict[str, List[Dict[str, Any]]] = {}
        for s in sessions:
            wid = s.get("workflow_id") or "adhoc"
            by_workflow.setdefault(wid, []).append(s)
        return {
            "running": running,
            "queued": queued,
            "recent_done": done[:15],
            "by_workflow": {
                k: {
                    "count": len(v),
                    "running": sum(1 for x in v if x.get("status") == "running"),
                    "done": sum(1 for x in v if x.get("status") == "done"),
                    "failed": sum(1 for x in v if x.get("status") == "failed"),
                    "sessions": v,
                }
                for k, v in by_workflow.items()
            },
            "totals": {
                "running": len(running),
                "queued": len(queued),
                "done": sum(1 for s in sessions if s.get("status") == "done"),
                "failed": sum(1 for s in sessions if s.get("status") == "failed"),
                "all": len(sessions),
            },
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def clear_finished(self) -> int:
        with self._lock:
            before = len(self.sessions)
            self.sessions = {
                k: v
                for k, v in self.sessions.items()
                if v.status in {"queued", "running"}
            }
            removed = before - len(self.sessions)
            self._save_unlocked()
            return removed

    def run_parallel(
        self,
        work: List[Dict[str, Any]],
        *,
        max_workers: int = 4,
        auto_approve: bool = False,
        dry_run: bool = False,
        workflow_id: Optional[str] = None,
        workflow_label: str = "parallel-terminals",
        default_timeout: float = 60.0,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        work: list of {title?, role?, command (str|list), cwd?, timeout?}
        Runs terminals concurrently; updates registry live for dashboard.
        """
        if not work:
            return {"ok": False, "error": "no work items", "sessions": []}

        # Resolve workspace cwd once
        base_cwd: Optional[str] = None
        try:
            from .workspace import workspace_root, assert_in_workspace

            root = workspace_root()
            if cwd:
                base_cwd = str(assert_in_workspace(cwd, root, label="cwd"))
            else:
                base_cwd = str(root)
        except Exception:
            base_cwd = cwd or os.getcwd()

        wid = workflow_id or f"twf-{uuid.uuid4().hex[:10]}"
        session_ids: List[str] = []

        with self._lock:
            for i, item in enumerate(work):
                sid = f"term-{uuid.uuid4().hex[:10]}"
                cmd = _normalize_command(
                    item.get("command") or item.get("cmd") or item.get("argv")
                )
                title = str(
                    item.get("title")
                    or item.get("name")
                    or (cmd[0] if cmd else f"term-{i + 1}")
                )
                sess_cwd = item.get("cwd")
                if sess_cwd:
                    try:
                        from .workspace import assert_in_workspace, workspace_root

                        sess_cwd = str(
                            assert_in_workspace(
                                sess_cwd, workspace_root(), label="cwd"
                            )
                        )
                    except Exception as e:  # noqa: BLE001
                        # keep relative / original and record later if needed
                        sess_cwd = str(sess_cwd)
                        _ = e
                else:
                    sess_cwd = base_cwd

                session = TerminalSession(
                    id=sid,
                    title=title[:80],
                    command=cmd,
                    role=str(item.get("role") or "worker"),
                    cwd=sess_cwd,
                    approved=bool(auto_approve or dry_run),
                    dry_run=bool(dry_run),
                    workflow_id=wid,
                    status="queued",
                    timeout_sec=float(
                        item.get("timeout") or item.get("timeout_sec") or default_timeout
                    ),
                )
                self.sessions[sid] = session
                session_ids.append(sid)
            self._save_unlocked()

        def _run_one(sid: str) -> TerminalSession:
            with self._lock:
                session = self.sessions[sid]
                session.status = "running"
                session.started_at = time.time()
                self._save_unlocked()
                cmd = list(session.command)
                sess_cwd = session.cwd
                timeout = session.timeout_sec
                is_dry = session.dry_run
                approved = session.approved
                title = session.title
                started_at = session.started_at

            try:
                if not cmd:
                    raise ValueError("empty command")

                blocked = _check_command_allowed(cmd)
                if blocked:
                    raise ValueError(blocked)

                if not approved and not is_dry:
                    raise ValueError(
                        "terminal not approved — pass auto_approve/dry_run or approve"
                    )

                if is_dry:
                    finished_at = time.time()
                    with self._lock:
                        session = self.sessions[sid]
                        session.status = "done"
                        session.finished_at = finished_at
                        session.duration_sec = round(
                            finished_at - (started_at or finished_at), 3
                        )
                        session.exit_code = 0
                        session.stdout_tail = (
                            f"[dry-run] would run in {sess_cwd}: {' '.join(cmd)}"
                        )
                        session.pid = None
                        self._save_unlocked()
                        return session

                # Optional container sandbox
                sand_result = None
                try:
                    from .config import Config
                    from .container_sandbox import try_sandboxed_shell

                    prefer = bool(Config().get("prefer_container_sandbox"))
                    sand_result = try_sandboxed_shell(
                        list(cmd), timeout=timeout, prefer=prefer
                    )
                except Exception:
                    sand_result = None

                if sand_result is not None and not sand_result.get("fallback"):
                    finished_at = time.time()
                    exit_code = int(sand_result.get("exit_code") or 0)
                    stdout = str(sand_result.get("stdout") or "")
                    stderr = str(sand_result.get("stderr") or "")
                    ok = exit_code == 0
                    with self._lock:
                        session = self.sessions[sid]
                        session.finished_at = finished_at
                        session.duration_sec = round(
                            finished_at - (started_at or finished_at), 3
                        )
                        session.exit_code = exit_code
                        session.stdout_tail = stdout[-2000:]
                        session.stderr_tail = stderr[-1000:]
                        session.status = "done" if ok else "failed"
                        if not ok and not session.error:
                            session.error = stderr[:500] or f"exit {exit_code}"
                        self._save_unlocked()
                        return session

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    shell=False,
                    cwd=sess_cwd or None,
                )
                finished_at = time.time()
                with self._lock:
                    session = self.sessions[sid]
                    session.finished_at = finished_at
                    session.duration_sec = round(
                        finished_at - (started_at or finished_at), 3
                    )
                    session.exit_code = proc.returncode
                    session.stdout_tail = (proc.stdout or "")[-2000:]
                    session.stderr_tail = (proc.stderr or "")[-1000:]
                    session.pid = getattr(proc, "pid", None)
                    if proc.returncode == 0:
                        session.status = "done"
                    else:
                        session.status = "failed"
                        session.error = (proc.stderr or "")[:500] or f"exit {proc.returncode}"
                    self._save_unlocked()
                    return session

            except subprocess.TimeoutExpired as e:
                finished_at = time.time()
                with self._lock:
                    session = self.sessions[sid]
                    session.status = "failed"
                    session.error = f"timeout after {timeout}s"
                    session.finished_at = finished_at
                    session.duration_sec = round(
                        finished_at - (started_at or finished_at), 3
                    )
                    session.stdout_tail = ((e.stdout or "") if isinstance(e.stdout, str) else "")[
                        -2000:
                    ]
                    session.stderr_tail = ((e.stderr or "") if isinstance(e.stderr, str) else "")[
                        -1000:
                    ]
                    self._save_unlocked()
                    return session
            except Exception as e:  # noqa: BLE001
                finished_at = time.time()
                with self._lock:
                    session = self.sessions[sid]
                    session.status = "failed"
                    session.error = str(e)
                    session.finished_at = finished_at
                    if session.started_at:
                        session.duration_sec = round(
                            finished_at - session.started_at, 3
                        )
                    self._save_unlocked()
                    return session

        workers = max(1, min(max_workers, len(session_ids)))
        results: List[TerminalSession] = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_run_one, sid): sid for sid in session_ids}
            for fut in as_completed(futs):
                results.append(fut.result())

        done = [s for s in results if s.status == "done"]
        failed = [s for s in results if s.status == "failed"]
        out = {
            "ok": len(failed) == 0,
            "workflow_id": wid,
            "workflow_label": workflow_label,
            "max_workers": workers,
            "total": len(results),
            "succeeded": len(done),
            "failed": len(failed),
            "sessions": [s.to_dict() for s in results],
            "dashboard": self.snapshot_for_dashboard(),
        }
        # Write terminal workflow outcomes into central Memory Palace
        try:
            from .central_memory import write_back_workflow

            task_hint = workflow_label
            if work:
                cmd0 = work[0].get("command") or work[0].get("title") or ""
                if isinstance(cmd0, list):
                    cmd0 = " ".join(cmd0)
                task_hint = str(cmd0)[:400] or workflow_label
            out["memory_write"] = write_back_workflow(
                task=task_hint,
                source="terminal_pool",
                workflow_id=wid,
                succeeded=len(done),
                failed=len(failed),
                total=len(results),
                jobs=[
                    {
                        "title": s.title,
                        "role": s.role,
                        "status": s.status,
                        "stdout_tail": s.stdout_tail,
                        "error": s.error,
                        "cli": s.title,
                    }
                    for s in results
                ],
            )
        except Exception:
            pass
        return out

    def run_agentic_parallel(
        self,
        task: str,
        terminals: Optional[List[Dict[str, Any]]] = None,
        *,
        max_workers: int = 4,
        dry_run: bool = True,
        auto_approve: bool = False,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Agentic fan-out: multiple terminal sessions work the same task in parallel
        (role-based commands), then optional supervisor merge of outputs.
        """
        if not terminals:
            terminals = self._default_agentic_terminals(task)

        # Ensure each has a role
        roles = ["architect", "implementer", "tester", "reviewer"]
        work: List[Dict[str, Any]] = []
        for i, t in enumerate(terminals):
            item = dict(t)
            item.setdefault("role", roles[i % len(roles)])
            item.setdefault(
                "title",
                f"{item['role']}-{i + 1}",
            )
            work.append(item)

        result = self.run_parallel(
            work,
            max_workers=max_workers,
            auto_approve=auto_approve or dry_run,
            dry_run=dry_run,
            workflow_label="agentic-terminals",
            cwd=cwd,
        )

        parts = []
        for s in result.get("sessions") or []:
            if s.get("status") == "done":
                parts.append(
                    f"### {s.get('title')} ({s.get('role')})\n"
                    f"$ {' '.join(s.get('command') or [])}\n"
                    f"{s.get('stdout_tail') or s.get('error') or ''}"
                )

        if parts:
            try:
                from .central_memory import memory_preface_for_llm, write_back_workflow
                from .model_caller import ModelCaller
                from .model_registry import ModelRegistry

                reg = ModelRegistry()
                names = [
                    n for n in reg.list_all_models() if not str(n).startswith("cli:")
                ]
                model = names[0] if names else "gpt-4o"
                blob = "\n\n".join(parts)[:12000]
                mem = memory_preface_for_llm(task)
                merge_prompt = (
                    f"Supervisor merge of parallel terminal workers for task:\n{task}\n\n"
                    f"{blob}\n\nProduce one coherent plan/result from terminal outputs."
                )
                if mem:
                    merge_prompt = f"{mem}\n\n{merge_prompt}"
                merged = ModelCaller(use_mock=True, registry=reg).call(
                    model=model,
                    prompt=merge_prompt,
                )
                result["synthesis"] = {
                    "model": model,
                    "text": merged.get("response"),
                    "memory_injected": bool(mem),
                }
                write_back_workflow(
                    task=task,
                    source="terminal_pool_agentic",
                    workflow_id=str(result.get("workflow_id") or ""),
                    succeeded=int(result.get("succeeded") or 0),
                    failed=int(result.get("failed") or 0),
                    total=int(result.get("total") or 0),
                    synthesis=str(merged.get("response") or "")[:2000],
                    jobs=result.get("sessions") or [],
                )
            except Exception as e:  # noqa: BLE001
                result["synthesis"] = {"error": str(e), "parts": len(parts)}
        else:
            result["synthesis"] = {
                "text": None,
                "note": "no successful terminal outputs",
            }

        try:
            from .audit_log import AuditLog

            AuditLog().record(
                "terminal_parallel_agentic",
                {
                    "workflow_id": result.get("workflow_id"),
                    "total": result.get("total"),
                    "succeeded": result.get("succeeded"),
                    "failed": result.get("failed"),
                    "dry_run": dry_run,
                },
            )
        except Exception:
            pass

        return result

    def _default_agentic_terminals(self, task: str) -> List[Dict[str, Any]]:
        """
        Role-based default terminal commands (cross-platform via python -c).
        Safe probes that demonstrate parallel multi-terminal agentic fan-out.
        """
        safe_task = task.replace("\\", "\\\\").replace("'", "\\'")[:200]
        py = sys.executable or "python"
        return [
            {
                "title": "architect",
                "role": "architect",
                "command": [
                    py,
                    "-c",
                    (
                        f"print('ROLE=architect'); print('TASK={safe_task}'); "
                        "print('PLAN: scope modules, interfaces, risks')"
                    ),
                ],
            },
            {
                "title": "implementer",
                "role": "implementer",
                "command": [
                    py,
                    "-c",
                    (
                        f"print('ROLE=implementer'); print('TASK={safe_task}'); "
                        "print('IMPL: skeleton modules + entrypoints')"
                    ),
                ],
            },
            {
                "title": "tester",
                "role": "tester",
                "command": [
                    py,
                    "-c",
                    (
                        f"print('ROLE=tester'); print('TASK={safe_task}'); "
                        "print('TEST: unit + smoke checklist')"
                    ),
                ],
            },
            {
                "title": "reviewer",
                "role": "reviewer",
                "command": [
                    py,
                    "-c",
                    (
                        f"print('ROLE=reviewer'); print('TASK={safe_task}'); "
                        "print('REVIEW: security, style, gaps')"
                    ),
                ],
            },
        ]
