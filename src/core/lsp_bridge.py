"""Optional LSP bridge foundation (V6 N231) — no hard dependency."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import queue
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def available() -> bool:
    try:
        import lsprotocol  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False




def python_provider_status(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Probe an optional Python LSP with a bounded, non-failing check."""
    configured = os.environ.get("SUPERAI_PYTHON_LSP", "").strip()
    command: Optional[str] = configured or shutil.which("basedpyright-langserver") or shutil.which("pyright-langserver")
    if not command:
        return {"available": False, "language": "python", "reason": "no Python LSP provider found; install pyright/basedpyright or set SUPERAI_PYTHON_LSP", "capabilities": []}
    if configured and not Path(command).is_file():
        return {"available": False, "language": "python", "reason": f"configured provider not found: {command}", "capabilities": []}
    try:
        probe = subprocess.run([command, "--stdio"], input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "language": "python", "reason": f"provider probe failed: {exc}", "capabilities": []}
    return {"available": True, "language": "python", "provider": Path(command).name, "capabilities": ["diagnostics", "references (provider-advertised; advisory only)"], "probe_exit_code": probe.returncode}




def python_reference_counts(root: Path, candidates: List[Dict[str, Any]], timeout_seconds: float = 45.0) -> Dict[str, Any]:
    """Ask an optional pyright-compatible server for Python symbol references.

    The bounded result is only used to *remove* candidates that the server can
    prove referenced. A failed or incomplete probe never changes candidates.
    """
    configured = os.environ.get("SUPERAI_PYTHON_LSP", "").strip()
    command = configured or shutil.which("basedpyright-langserver") or shutil.which("pyright-langserver")
    if not command or (configured and not Path(command).is_file()):
        return {"available": False, "reason": "Python LSP provider unavailable", "reference_counts": {}}
    try:
        proc = subprocess.Popen([command, "--stdio"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError as exc:
        return {"available": False, "reason": f"provider start failed: {exc}", "reference_counts": {}}
    messages: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    def reader() -> None:
        assert proc.stdout is not None
        try:
            while True:
                headers: Dict[str, str] = {}
                while True:
                    line = proc.stdout.readline()
                    if not line:
                        return
                    line = line.decode("ascii", "replace").strip()
                    if not line:
                        break
                    key, _, value = line.partition(":")
                    headers[key.lower()] = value.strip()
                size = int(headers.get("content-length", "0"))
                payload = proc.stdout.read(size)
                value = json.loads(payload.decode("utf-8"))
                if isinstance(value, dict):
                    messages.put(value)
        except (OSError, ValueError, json.JSONDecodeError):
            return
    threading.Thread(target=reader, daemon=True).start()
    request_id = 0
    def request(method: str, params: Dict[str, Any], budget: float) -> Any:
        nonlocal request_id
        request_id += 1
        payload = json.dumps({"jsonrpc":"2.0","id":request_id,"method":method,"params":params}).encode("utf-8")
        assert proc.stdin is not None
        proc.stdin.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii") + payload); proc.stdin.flush()
        deadline = time.monotonic() + budget
        while True:
            item = messages.get(timeout=max(0.05, deadline - time.monotonic()))
            if item.get("id") == request_id:
                if "error" in item:
                    raise RuntimeError(str(item["error"]))
                return item.get("result")
    try:
        initialized = request("initialize", {"processId":None,"rootUri":root.resolve().as_uri(),"workspaceFolders":[{"uri":root.resolve().as_uri(),"name":root.name}],"capabilities":{}}, min(5.0, timeout_seconds)) or {}
        if not (initialized.get("capabilities") or {}).get("referencesProvider"):
            return {"available": False, "reason": "provider has no references capability", "reference_counts": {}}
        assert proc.stdin is not None
        init = json.dumps({"jsonrpc":"2.0","method":"initialized","params":{}}).encode("utf-8")
        proc.stdin.write(f"Content-Length: {len(init)}\r\n\r\n".encode("ascii") + init); proc.stdin.flush()
        counts: Dict[str, int] = {}
        deadline = time.monotonic() + timeout_seconds
        for item in candidates:
            source = root / str(item["file"]); name = str(item["name"]); line = int(item["line"]) - 1
            if source.suffix != ".py" or not source.is_file() or time.monotonic() >= deadline:
                continue
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            if line < 0 or line >= len(lines) or name not in lines[line]:
                continue
            uri = source.resolve().as_uri(); column = lines[line].index(name)
            open_payload = json.dumps({"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":uri,"languageId":"python","version":1,"text":"\n".join(lines)}}}).encode("utf-8")
            proc.stdin.write(f"Content-Length: {len(open_payload)}\r\n\r\n".encode("ascii") + open_payload); proc.stdin.flush()
            locations = request("textDocument/references", {"textDocument":{"uri":uri},"position":{"line":line,"character":column},"context":{"includeDeclaration":True}}, min(15.0, max(0.5, deadline-time.monotonic()))) or []
            counts[str(item["id"])] = len(locations) if isinstance(locations, list) else 0
        return {"available": True, "reference_counts": counts, "timed_out": time.monotonic() >= deadline}
    except (OSError, RuntimeError, TimeoutError, queue.Empty) as exc:
        return {"available": False, "reason": f"reference probe failed: {exc}", "reference_counts": {}}
    finally:
        proc.terminate()

def diagnostics_stub(path: str) -> Dict[str, Any]:
    """
    Without a running language server, return structure-only response.
    Real LSP wiring is optional when python-lsp / pyright present.
    """
    from pathlib import Path

    p = Path(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": path}
    # lightweight syntax-ish checks for Python
    diags: List[Dict[str, Any]] = []
    if p.suffix == ".py":
        try:
            compile(p.read_text(encoding="utf-8", errors="replace"), str(p), "exec")
        except SyntaxError as e:
            diags.append(
                {
                    "severity": "error",
                    "line": e.lineno or 1,
                    "message": e.msg,
                }
            )
    return {
        "ok": True,
        "path": str(p),
        "diagnostics": diags,
        "lsp_available": available(),
        "mode": "stub_or_compile",
    }
