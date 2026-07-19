"""
N208 expansion — OS process multiplexing (tmux-like panes).

Runs real subprocesses per pane with:
- stdin/stdout/stderr pipes (all platforms)
- Unix PTY when available (termios/pty)
- Windows process groups + optional ConPTY probe
- non-blocking read, write, kill, select, list
- persistence of pane metadata (not live FDs) under ~/.superai/tui/process_mux.json

This completes the former "not OS tmux" boundary with an in-process SuperAI
process multiplexer (no external tmux binary required; optional external
tmux/zellij attach helpers included).
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Sequence


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def process_mux_path() -> Path:
    p = Path.home() / ".superai" / "tui" / "process_mux.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class PaneSpec:
    id: str
    title: str
    command: List[str]
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    use_pty: bool = True
    created_at: str = ""
    session_id: str = ""  # optional SuperAI session link

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "command": list(self.command),
            "cwd": self.cwd,
            "env": dict(self.env or {}),
            "use_pty": self.use_pty,
            "created_at": self.created_at,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PaneSpec":
        return cls(
            id=str(d.get("id") or ""),
            title=str(d.get("title") or ""),
            command=list(d.get("command") or []),
            cwd=d.get("cwd"),
            env=dict(d.get("env") or {}),
            use_pty=bool(d.get("use_pty", True)),
            created_at=str(d.get("created_at") or ""),
            session_id=str(d.get("session_id") or ""),
        )


class ProcessPane:
    """One multiplexed process pane."""

    def __init__(self, spec: PaneSpec):
        self.spec = spec
        self.proc: Optional[subprocess.Popen] = None
        self.master_fd: Optional[int] = None  # unix pty
        self.conpty = None  # Windows ConPTYSession
        self._buf: Deque[str] = deque(maxlen=5000)
        self._lock = threading.Lock()
        self._reader: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.backend: str = "none"  # pipe | pty | conpty
        self.started_at: Optional[str] = None
        self.exit_code: Optional[int] = None

    @property
    def pid(self) -> Optional[int]:
        if self.conpty is not None:
            return getattr(self.conpty, "pid", None)
        return self.proc.pid if self.proc else None

    def alive(self) -> bool:
        if self.conpty is not None:
            try:
                return bool(self.conpty.alive())
            except Exception:
                return False
        if not self.proc:
            return False
        return self.proc.poll() is None

    def status(self) -> Dict[str, Any]:
        exit_code = self.exit_code
        if self.proc:
            exit_code = self.proc.poll()
        return {
            "id": self.spec.id,
            "title": self.spec.title,
            "command": self.spec.command,
            "pid": self.pid,
            "alive": self.alive(),
            "backend": self.backend,
            "started_at": self.started_at,
            "exit_code": exit_code,
            "buffer_lines": len(self._buf)
            if self.conpty is None
            else len(getattr(self.conpty, "_buf", self._buf)),
            "session_id": self.spec.session_id,
            "cwd": self.spec.cwd,
            "restorable": bool(self.spec.command),
        }

    def start(self) -> Dict[str, Any]:
        if self.alive():
            return {"ok": True, "already": True, **self.status()}
        cmd = list(self.spec.command)
        if not cmd:
            return {"ok": False, "error": "empty_command"}
        env = os.environ.copy()
        if self.spec.env:
            env.update({str(k): str(v) for k, v in self.spec.env.items()})
        cwd = self.spec.cwd or None
        self._stop.clear()
        self.conpty = None

        # Prefer Unix PTY
        if self.spec.use_pty and sys.platform != "win32":
            try:
                self._start_unix_pty(cmd, env, cwd)
                self.backend = "pty"
            except Exception:
                self._start_pipes(cmd, env, cwd)
                self.backend = "pipe"
        elif sys.platform == "win32" and self.spec.use_pty and conpty_available():
            # True Windows ConPTY pseudo-console
            try:
                from .tui_conpty import spawn_conpty

                sess, res = spawn_conpty(cmd, cwd=cwd, env=env)
                if res.get("ok") and sess is not None:
                    self.conpty = sess
                    self.backend = "conpty"
                else:
                    self._start_pipes(cmd, env, cwd)
                    self.backend = f"pipe(conpty_failed:{res.get('error', '?')[:40]})"
            except Exception as e:
                self._start_pipes(cmd, env, cwd)
                self.backend = f"pipe(conpty_exc:{str(e)[:40]})"
        else:
            self._start_pipes(cmd, env, cwd)
            self.backend = "pipe"

        self.started_at = _now()
        if self.conpty is None:
            self._reader = threading.Thread(target=self._read_loop, daemon=True)
            self._reader.start()
        return {"ok": True, **self.status()}

    def _start_unix_pty(self, cmd: List[str], env: dict, cwd: Optional[str]) -> None:
        import pty

        master, slave = pty.openpty()
        self.master_fd = master
        self.proc = subprocess.Popen(
            cmd,
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=cwd,
            env=env,
            close_fds=True,
            start_new_session=True,
        )
        try:
            os.close(slave)
        except Exception:
            pass

    def _start_pipes(self, cmd: List[str], env: dict, cwd: Optional[str]) -> None:
        kwargs: Dict[str, Any] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "cwd": cwd,
            "env": env,
            "bufsize": 0,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
            # text mode False for binary-safe
        self.proc = subprocess.Popen(cmd, **kwargs)

    def _read_loop(self) -> None:
        try:
            if self.master_fd is not None:
                self._read_fd(self.master_fd)
            elif self.proc and self.proc.stdout:
                self._read_stream(self.proc.stdout)
        finally:
            if self.proc:
                self.exit_code = self.proc.poll()

    def _read_fd(self, fd: int) -> None:
        while not self._stop.is_set():
            try:
                import select

                r, _, _ = select.select([fd], [], [], 0.2)
                if not r:
                    if self.proc and self.proc.poll() is not None:
                        break
                    continue
                data = os.read(fd, 4096)
                if not data:
                    break
                text = data.decode("utf-8", errors="replace")
                self._append(text)
            except Exception:
                break

    def _read_stream(self, stream) -> None:
        while not self._stop.is_set():
            try:
                data = stream.read(4096)
                if not data:
                    if self.proc and self.proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                if isinstance(data, bytes):
                    text = data.decode("utf-8", errors="replace")
                else:
                    text = str(data)
                self._append(text)
            except Exception:
                break

    def _append(self, text: str) -> None:
        with self._lock:
            for line in text.splitlines(keepends=True):
                self._buf.append(line)

    def read_output(self, *, max_chars: int = 8000, clear: bool = False) -> str:
        if self.conpty is not None:
            return self.conpty.read_output(max_chars=max_chars, clear=clear)
        with self._lock:
            data = "".join(self._buf)
            if clear:
                self._buf.clear()
            if len(data) > max_chars:
                data = data[-max_chars:]
            return data

    def write(self, data: str) -> Dict[str, Any]:
        if not self.alive():
            return {"ok": False, "error": "not_alive"}
        if self.conpty is not None:
            return self.conpty.write(data)
        payload = data if data.endswith("\n") or data.endswith("\r") else data
        try:
            raw = payload.encode("utf-8") if isinstance(payload, str) else payload
            if self.master_fd is not None:
                os.write(self.master_fd, raw if isinstance(raw, bytes) else str(raw).encode())
            elif self.proc and self.proc.stdin:
                self.proc.stdin.write(raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode())
                self.proc.stdin.flush()
            else:
                return {"ok": False, "error": "no_stdin"}
            return {"ok": True, "bytes": len(raw)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}

    def kill(self, *, force: bool = False) -> Dict[str, Any]:
        self._stop.set()
        if self.conpty is not None:
            out = self.conpty.kill()
            self.conpty = None
            self.exit_code = out.get("exit_code")
            return {**out, "id": self.spec.id}
        if not self.proc:
            return {"ok": True, "killed": False, "message": "no_process"}
        try:
            if sys.platform == "win32":
                try:
                    self.proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                except Exception:
                    pass
                time.sleep(0.2)
                if self.proc.poll() is None:
                    self.proc.kill()
            else:
                try:
                    os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
                except Exception:
                    self.proc.terminate()
                time.sleep(0.2)
                if self.proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
                    except Exception:
                        self.proc.kill()
            code = self.proc.poll()
            self.exit_code = code
        except Exception as e:
            return {"ok": False, "error": str(e)[:200]}
        finally:
            if self.master_fd is not None:
                try:
                    os.close(self.master_fd)
                except Exception:
                    pass
                self.master_fd = None
        return {"ok": True, "killed": True, "exit_code": self.exit_code, "id": self.spec.id}


def conpty_available() -> bool:
    """True when Windows ConPTY API is usable."""
    if sys.platform != "win32":
        return False
    try:
        from .tui_conpty import conpty_supported

        return bool(conpty_supported())
    except Exception:
        try:
            import ctypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            return hasattr(kernel32, "CreatePseudoConsole")
        except Exception:
            return False


def default_shell_command() -> List[str]:
    if sys.platform == "win32":
        comspec = os.environ.get("COMSPEC") or "cmd.exe"
        return [comspec]
    shell = os.environ.get("SHELL") or "/bin/bash"
    return [shell, "-l"]


class ProcessMux:
    """
    tmux-like process multiplexer managed by SuperAI.
    """

    def __init__(self, *, persist: bool = True, auto_restore: Optional[bool] = None):
        self.persist = persist
        self.panes: Dict[str, ProcessPane] = {}
        self.active_id: Optional[str] = None
        self.name: str = "proc-default"
        self._saved_specs: List[PaneSpec] = []
        self._load_meta()
        # Auto-restore when SUPERAI_PMUX_RESTORE=1 (or explicit auto_restore=True)
        if auto_restore is None:
            auto_restore = (os.getenv("SUPERAI_PMUX_RESTORE") or "").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        if auto_restore and self._saved_specs:
            self.restore(start=True)

    def _load_meta(self) -> None:
        path = process_mux_path()
        self._saved_specs = []
        if not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.name = str(data.get("name") or self.name)
            self.active_id = data.get("active_id")
            self._saved_specs = [
                PaneSpec.from_dict(p) for p in (data.get("panes") or []) if isinstance(p, dict)
            ]
        except Exception:
            self._saved_specs = []

    def _save_meta(self) -> None:
        if not self.persist:
            return
        # Merge live panes + any saved specs not currently live (preserve restore list)
        by_id: Dict[str, Dict[str, Any]] = {}
        for spec in self._saved_specs:
            if spec.id and spec.command:
                by_id[spec.id] = spec.to_dict()
        for p in self.panes.values():
            d = p.spec.to_dict()
            d["last_pid"] = p.pid
            d["alive"] = p.alive()
            d["backend"] = p.backend
            by_id[p.spec.id] = d
            # keep saved specs in sync
            self._upsert_saved(p.spec)
        path = process_mux_path()
        path.write_text(
            json.dumps(
                {
                    "name": self.name,
                    "active_id": self.active_id,
                    "panes": list(by_id.values()),
                    "updated_at": _now(),
                    "platform": sys.platform,
                    "conpty_available": conpty_available(),
                    "conpty_backend": "conpty" if conpty_available() else "pipe",
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _upsert_saved(self, spec: PaneSpec) -> None:
        for i, s in enumerate(self._saved_specs):
            if s.id == spec.id:
                self._saved_specs[i] = spec
                return
        self._saved_specs.append(spec)

    def saved_specs(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._saved_specs]

    def restore(
        self,
        *,
        start: bool = True,
        only_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """
        Resurrect process panes from persisted metadata.

        start=True spawns each command again (new PIDs). Specs without a command are skipped.
        """
        from .spend_guard import ensure_public_result

        want = set(only_ids) if only_ids else None
        restored = []
        errors = []
        for spec in list(self._saved_specs):
            if want is not None and spec.id not in want:
                continue
            if not spec.command:
                errors.append({"id": spec.id, "error": "no_command"})
                continue
            if spec.id in self.panes and self.panes[spec.id].alive():
                restored.append({"id": spec.id, "already_alive": True})
                continue
            pane = ProcessPane(spec)
            self.panes[spec.id] = pane
            if self.active_id is None:
                self.active_id = spec.id
            entry: Dict[str, Any] = {"id": spec.id, "title": spec.title, "command": spec.command}
            if start:
                entry["start"] = pane.start()
                entry["ok"] = bool(entry["start"].get("ok"))
                if not entry["ok"]:
                    errors.append(entry)
                else:
                    restored.append(entry)
            else:
                entry["ok"] = True
                entry["started"] = False
                restored.append(entry)
        if restored and self.active_id not in self.panes:
            self.active_id = next(iter(self.panes), None)
        self._save_meta()
        return ensure_public_result(
            {
                "ok": len(errors) == 0,
                "restored": restored,
                "errors": errors,
                "pane_count": len(self.panes),
                "active_id": self.active_id,
                "bar": self.status_bar(),
            },
            ok=len(errors) == 0 or len(restored) > 0,
        )

    def status(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        return ensure_public_result(
            {
                "ok": True,
                "name": self.name,
                "active_id": self.active_id,
                "pane_count": len(self.panes),
                "panes": [p.status() for p in self.panes.values()],
                "saved_count": len(self._saved_specs),
                "saved": self.saved_specs(),
                "bar": self.status_bar(),
                "platform": sys.platform,
                "conpty_available": conpty_available(),
                "conpty": (
                    {"supported": True, "module": "core.tui_conpty"}
                    if conpty_available()
                    else {"supported": False}
                ),
                "external": external_mux_tools(),
                "path": str(process_mux_path()),
                "auto_restore_env": os.getenv("SUPERAI_PMUX_RESTORE") or "",
            },
            ok=True,
        )

    def status_bar(self) -> str:
        if not self.panes:
            return f"[{self.name}] (no process panes)"
        parts = []
        for i, (pid, pane) in enumerate(self.panes.items()):
            mark = "*" if pane.spec.id == self.active_id else " "
            live = "•" if pane.alive() else "○"
            parts.append(f"{mark}{live}{i}:{pane.spec.title[:14]}")
        return f"[{self.name}] " + " | ".join(parts)

    def active(self) -> Optional[ProcessPane]:
        if self.active_id and self.active_id in self.panes:
            return self.panes[self.active_id]
        if self.panes:
            self.active_id = next(iter(self.panes))
            return self.panes[self.active_id]
        return None

    def spawn(
        self,
        command: Optional[Sequence[str]] = None,
        *,
        title: str = "",
        cwd: Optional[str] = None,
        shell: bool = False,
        session_id: str = "",
        use_pty: bool = True,
        start: bool = True,
    ) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        if shell or not command:
            cmd = default_shell_command()
        else:
            cmd = list(command)
        if len(cmd) == 1 and " " in cmd[0] and sys.platform == "win32":
            # allow "cmd /c dir" style single string via shell
            cmd = default_shell_command()[:1] + ["/c", command[0]] if command else cmd

        pid = f"p-{uuid.uuid4().hex[:8]}"
        spec = PaneSpec(
            id=pid,
            title=(title or (cmd[0] if cmd else pid))[:80],
            command=cmd,
            cwd=cwd,
            use_pty=use_pty,
            created_at=_now(),
            session_id=session_id or "",
        )
        pane = ProcessPane(spec)
        self.panes[pid] = pane
        self.active_id = pid
        self._upsert_saved(spec)
        result: Dict[str, Any] = {"ok": True, "created": spec.to_dict()}
        if start:
            result["start"] = pane.start()
            result["ok"] = bool(result["start"].get("ok"))
            result["backend"] = pane.backend
        self._save_meta()
        result["bar"] = self.status_bar()
        result["active_id"] = self.active_id
        return ensure_public_result(result, ok=result["ok"])

    def spawn_shell(self, *, title: str = "shell", cwd: Optional[str] = None) -> Dict[str, Any]:
        return self.spawn(None, title=title, cwd=cwd, shell=True)

    def spawn_superai(
        self,
        args: Optional[Sequence[str]] = None,
        *,
        title: str = "superai",
    ) -> Dict[str, Any]:
        """Spawn `python -m scli <args>` or superai on PATH."""
        if shutil.which("superai"):
            cmd = ["superai"] + list(args or ["status"])
        else:
            cmd = [sys.executable, "-m", "scli"] + list(args or ["status"])
        return self.spawn(cmd, title=title, use_pty=True)

    def select(self, pane_id: str) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        # allow index
        if pane_id.isdigit():
            keys = list(self.panes.keys())
            i = int(pane_id)
            if 0 <= i < len(keys):
                pane_id = keys[i]
        if pane_id not in self.panes:
            return ensure_public_result(
                {"ok": False, "error": "pane_not_found", "id": pane_id}, ok=False
            )
        self.active_id = pane_id
        self._save_meta()
        return ensure_public_result(
            {
                "ok": True,
                "active_id": self.active_id,
                "pane": self.panes[pane_id].status(),
                "bar": self.status_bar(),
            },
            ok=True,
        )

    def next_pane(self) -> Dict[str, Any]:
        keys = list(self.panes.keys())
        if not keys:
            from .spend_guard import ensure_public_result

            return ensure_public_result({"ok": False, "error": "no_panes"}, ok=False)
        if self.active_id not in keys:
            return self.select(keys[0])
        i = keys.index(self.active_id)
        return self.select(keys[(i + 1) % len(keys)])

    def prev_pane(self) -> Dict[str, Any]:
        keys = list(self.panes.keys())
        if not keys:
            from .spend_guard import ensure_public_result

            return ensure_public_result({"ok": False, "error": "no_panes"}, ok=False)
        if self.active_id not in keys:
            return self.select(keys[0])
        i = keys.index(self.active_id)
        return self.select(keys[(i - 1) % len(keys)])

    def kill(self, pane_id: Optional[str] = None, *, force: bool = False) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        pid = pane_id or self.active_id
        if not pid or pid not in self.panes:
            return ensure_public_result({"ok": False, "error": "pane_not_found"}, ok=False)
        # Keep spec in _saved_specs for restore; only stop the live process
        spec = self.panes[pid].spec
        self._upsert_saved(spec)
        out = self.panes[pid].kill(force=force)
        del self.panes[pid]
        if self.active_id == pid:
            self.active_id = next(iter(self.panes), None)
        self._save_meta()
        return ensure_public_result({**out, "bar": self.status_bar()}, ok=bool(out.get("ok")))

    def kill_all(self) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        results = []
        for pid in list(self.panes.keys()):
            results.append(self.kill(pid))
        return ensure_public_result({"ok": True, "killed": results, "bar": self.status_bar()}, ok=True)

    def write(self, data: str, *, pane_id: Optional[str] = None) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        pane = self.panes.get(pane_id or self.active_id or "")
        if not pane:
            return ensure_public_result({"ok": False, "error": "no_active_pane"}, ok=False)
        return ensure_public_result(pane.write(data), ok=True)

    def read(self, *, pane_id: Optional[str] = None, max_chars: int = 8000, clear: bool = False) -> Dict[str, Any]:
        from .spend_guard import ensure_public_result

        pane = self.panes.get(pane_id or self.active_id or "")
        if not pane:
            return ensure_public_result({"ok": False, "error": "no_active_pane"}, ok=False)
        text = pane.read_output(max_chars=max_chars, clear=clear)
        return ensure_public_result(
            {
                "ok": True,
                "id": pane.spec.id,
                "output": text,
                "alive": pane.alive(),
                "backend": pane.backend,
            },
            ok=True,
        )

    def link_session(self, session_id: str, *, pane_id: Optional[str] = None) -> Dict[str, Any]:
        """Link a process pane to a SuperAI agent session (N208 session mux bridge)."""
        from .spend_guard import ensure_public_result

        pane = self.panes.get(pane_id or self.active_id or "")
        if not pane:
            return ensure_public_result({"ok": False, "error": "no_active_pane"}, ok=False)
        pane.spec.session_id = session_id
        self._save_meta()
        # also attach into SessionMux
        try:
            from .tui_mux import SessionMux

            SessionMux(persist=True).attach(session_id, title=pane.spec.title)
        except Exception:
            pass
        return ensure_public_result(
            {"ok": True, "pane": pane.status(), "session_id": session_id}, ok=True
        )


def external_mux_tools() -> Dict[str, Any]:
    """Detect host multiplexers for optional attach helpers."""
    tools = {}
    for name in ("tmux", "zellij", "screen"):
        path = shutil.which(name)
        tools[name] = {"available": bool(path), "path": path}
    return tools


def tmux_new_session(name: str = "superai", command: Optional[str] = None) -> Dict[str, Any]:
    """Optional: create a real tmux session when tmux is installed."""
    from .spend_guard import ensure_public_result

    tmux = shutil.which("tmux")
    if not tmux:
        return ensure_public_result(
            {"ok": False, "error": "tmux_not_found", "hint": "Install tmux or use process-mux spawn"},
            ok=False,
        )
    cmd = [tmux, "new-session", "-d", "-s", name]
    if command:
        cmd += [command]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return ensure_public_result(
            {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": (proc.stdout or "")[:500],
                "stderr": (proc.stderr or "")[:500],
                "attach": f"tmux attach -t {name}",
            },
            ok=proc.returncode == 0,
        )
    except Exception as e:
        return ensure_public_result({"ok": False, "error": str(e)[:200]}, ok=False)


PROCESS_MUX_HELP = """
### Process mux (N208 OS-level panes)

| Command | Action |
|---------|--------|
| `/pmux` `/pmux status` | List process panes |
| `/pmux shell [title]` | Spawn interactive shell pane |
| `/pmux spawn <cmd…>` | Spawn command |
| `/pmux superai [args…]` | Spawn SuperAI CLI pane |
| `/pmux select <id\\|n>` | Select pane |
| `/pmux next` `/pmux prev` | Cycle panes |
| `/pmux write <text>` | Send input to active pane |
| `/pmux read` | Read buffered output |
| `/pmux kill [id]` | Kill pane |
| `/pmux kill-all` | Kill all panes |
| `/pmux link <session_id>` | Link pane ↔ SuperAI session |
| `/pmux tmux [name]` | Create external tmux session if installed |
| `/pmux restore` | Respawn panes from saved metadata |
| `/pmux help` | This help |

CLI: `superai process-mux status|shell|spawn|read|write|kill|restore|…`

Backends: Unix **PTY**; Windows **ConPTY** (true pseudo-console) with pipe fallback.
Restore: `SUPERAI_PMUX_RESTORE=1` auto-respawns saved panes on ProcessMux init.
"""


def handle_pmux_slash(arg: str = "", *, mux: Optional[ProcessMux] = None) -> Dict[str, Any]:
    from .spend_guard import ensure_public_result

    mux = mux or ProcessMux(persist=True)
    parts = (arg or "").strip().split()
    sub = (parts[0] if parts else "status").lower()
    rest = parts[1:]

    if sub in {"", "status", "st", "list", "ls"}:
        return {**mux.status(), "handled": True}
    if sub in {"shell", "sh"}:
        title = " ".join(rest) if rest else "shell"
        return {**mux.spawn_shell(title=title), "handled": True}
    if sub in {"spawn", "run", "exec"}:
        if not rest:
            return ensure_public_result(
                {"ok": False, "handled": True, "error": "usage: /pmux spawn <cmd…>"}, ok=False
            )
        # on Windows, join as shell command for convenience
        if sys.platform == "win32" and len(rest) > 0:
            return {
                **mux.spawn(
                    [os.environ.get("COMSPEC", "cmd.exe"), "/c", " ".join(rest)],
                    title=rest[0][:40],
                ),
                "handled": True,
            }
        return {**mux.spawn(rest, title=rest[0][:40]), "handled": True}
    if sub in {"superai", "sai"}:
        return {**mux.spawn_superai(rest or ["status"]), "handled": True}
    if sub in {"select", "s"}:
        return {**mux.select(rest[0] if rest else "0"), "handled": True}
    if sub in {"next", "n"}:
        return {**mux.next_pane(), "handled": True}
    if sub in {"prev", "p"}:
        return {**mux.prev_pane(), "handled": True}
    if sub in {"write", "send", "w"}:
        return {**mux.write(" ".join(rest)), "handled": True}
    if sub in {"read", "out", "capture"}:
        return {**mux.read(), "handled": True}
    if sub in {"kill", "x"}:
        return {**mux.kill(rest[0] if rest else None), "handled": True}
    if sub in {"kill-all", "killall"}:
        return {**mux.kill_all(), "handled": True}
    if sub in {"link"}:
        return {**mux.link_session(rest[0] if rest else ""), "handled": True}
    if sub in {"tmux"}:
        return {**tmux_new_session(rest[0] if rest else "superai"), "handled": True}
    if sub in {"restore", "respawn"}:
        only = rest if rest else None
        return {**mux.restore(start=True, only_ids=only), "handled": True}
    if sub in {"saved", "meta"}:
        return ensure_public_result(
            {
                "ok": True,
                "handled": True,
                "saved": mux.saved_specs(),
                "path": str(process_mux_path()),
            },
            ok=True,
        )
    if sub in {"help", "?"}:
        return ensure_public_result({"ok": True, "handled": True, "help": PROCESS_MUX_HELP}, ok=True)
    return ensure_public_result(
        {
            "ok": False,
            "handled": True,
            "error": "unknown_pmux_subcommand",
            "help": "status|shell|spawn|superai|select|next|prev|write|read|kill|kill-all|link|tmux|restore|saved|help",
        },
        ok=False,
    )
