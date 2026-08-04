"""Optional LSP bridge foundation (V6 N231) — no hard dependency."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import queue
import time
import tempfile
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


_LANGUAGE_PROVIDERS = {
    "python": ("SUPERAI_PYTHON_LSP", ["basedpyright-langserver", "pyright-langserver"], {".py"}, "python"),
    "typescript_javascript": ("SUPERAI_TYPESCRIPT_LSP", ["typescript-language-server"], {".ts", ".tsx", ".js", ".jsx"}, "typescript"),
    "go": ("SUPERAI_GO_LSP", ["gopls"], {".go"}, "go"),
    "rust": ("SUPERAI_RUST_LSP", ["rust-analyzer"], {".rs"}, "rust"),
    "csharp": ("SUPERAI_CSHARP_LSP", ["roslyn-language-server", "csharp-ls"], {".cs"}, "csharp"),
}

def available() -> bool:
    try:
        import lsprotocol  # type: ignore  # noqa: F401

        return True
    except Exception:
        return False






def _provider_command(environment_name: str, commands: List[str]) -> Optional[str]:
    configured = os.environ.get(environment_name, "").strip()
    if configured:
        return configured if Path(configured).is_file() else None
    for command in commands:
        found = shutil.which(command)
        if found:
            return found
    user_bins = [
        Path.home() / "go" / "bin",
        Path.home() / ".cargo" / "bin",
        Path.home() / ".dotnet" / "tools",
        Path(os.environ.get("APPDATA", "")) / "npm",
        Path(sys.executable).parent / "Scripts",
    ]
    for scripts in user_bins:
        for command in commands:
            candidate = scripts / f"{command}.exe"
            if candidate.is_file():
                return str(candidate)
    return None


def typescript_provider_status(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Report the optional TypeScript/JavaScript LSP without installing it."""
    command = _provider_command("SUPERAI_TYPESCRIPT_LSP", ["typescript-language-server"])
    if not command:
        return {"available": False, "language": "typescript_javascript", "reason": "typescript-language-server not found", "capabilities": []}
    try:
        probe = subprocess.run([command, "--stdio"], input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "language": "typescript_javascript", "reason": f"provider probe failed: {exc}", "capabilities": []}
    return {"available": True, "language": "typescript_javascript", "provider": Path(command).name, "capabilities": ["diagnostics", "references (advisory only)"], "probe_exit_code": probe.returncode}

def python_provider_status(timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """Probe an optional Python LSP with a bounded, non-failing check."""
    configured = os.environ.get("SUPERAI_PYTHON_LSP", "").strip()
    command: Optional[str] = _provider_command("SUPERAI_PYTHON_LSP", ["basedpyright-langserver", "pyright-langserver"])
    if not command:
        reason = f"configured provider not found: {configured}" if configured else "no Python LSP provider found; install pyright/basedpyright or set SUPERAI_PYTHON_LSP"
        return {"available": False, "language": "python", "reason": reason, "capabilities": []}
    if configured and not Path(command).is_file():
        return {"available": False, "language": "python", "reason": f"configured provider not found: {command}", "capabilities": []}
    try:
        probe = subprocess.run([command, "--stdio"], input=b"", stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=timeout_seconds, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "language": "python", "reason": f"provider probe failed: {exc}", "capabilities": []}
    return {"available": True, "language": "python", "provider": Path(command).name, "capabilities": ["diagnostics", "references (provider-advertised; advisory only)"], "probe_exit_code": probe.returncode}




def _java_server_command(root: Path) -> Optional[List[str]]:
    """Build the JDT LS command when the official archive is installed locally."""
    home = Path(os.environ.get("SUPERAI_JDTLS_HOME", "") or Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "jdtls")
    launchers = sorted((home / "plugins").glob("org.eclipse.equinox.launcher_*.jar"))
    config = home / "config_win"
    java = _provider_command("SUPERAI_JAVA_EXECUTABLE", ["java"])
    if not java:
        redhat = Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "RedHat"
        matches = sorted(redhat.glob("java-*\\bin\\java.exe"))
        java = str(matches[-1]) if matches else None
    if not java or not launchers or not config.is_dir():
        return None
    workspace = Path(tempfile.gettempdir()) / "superai-jdtls" / hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:16]
    workspace.mkdir(parents=True, exist_ok=True)
    return [java, "-Declipse.application=org.eclipse.jdt.ls.core.id1", "-Dosgi.bundles.defaultStartLevel=4", "-Declipse.product=org.eclipse.jdt.ls.core.product", "-Xmx1G", "-jar", str(launchers[-1]), "-configuration", str(config), "-data", str(workspace)]


def _server_environment(language: str) -> Dict[str, str]:
    """Provide discovered toolchains to language-server child processes."""
    environment = dict(os.environ)
    extra_paths = []
    if language == "go":
        extra_paths.append(str(Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Go" / "bin"))
    elif language == "rust":
        extra_paths.append(str(Path.home() / ".cargo" / "bin"))
    elif language == "csharp":
        extra_paths.extend([str(Path.home() / ".dotnet" / "tools"), str(Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "dotnet")])
    existing = environment.get("PATH", "")
    environment["PATH"] = os.pathsep.join([*extra_paths, existing])
    return environment

def provider_status(language: str) -> Dict[str, Any]:
    """Return provider discovery state without starting or installing a server."""
    if language == "java":
        command = _java_server_command(Path.cwd())
        if command:
            return {"available": True, "language": language, "provider": "jdtls", "capabilities": ["diagnostics", "references (advisory only)"]}
        return {"available": False, "language": language, "reason": "Eclipse JDT LS or Java runtime not found", "capabilities": []}
    provider = _LANGUAGE_PROVIDERS.get(language)
    if not provider:
        return {"available": False, "language": language, "reason": f"unsupported LSP language: {language}", "capabilities": []}
    environment_name, commands, _, _ = provider
    command = _provider_command(environment_name, commands)
    if not command:
        return {"available": False, "language": language, "reason": f"{commands[0]} not found", "capabilities": []}
    return {"available": True, "language": language, "provider": Path(command).name, "capabilities": ["diagnostics", "references (advisory only)"]}


def all_provider_statuses() -> Dict[str, Dict[str, Any]]:
    return {language: provider_status(language) for language in ["python", "typescript_javascript", "go", "rust", "java", "csharp"]}

def _omnisharp_reference_counts(command: str, root: Path, candidates: List[Dict[str, Any]], timeout_seconds: float) -> Dict[str, Any]:
    """Use OmniSharp's native stdio /findusages protocol as a C# adapter."""
    try:
        proc = subprocess.Popen([command, "-s", str(root)], cwd=str(root), env=_server_environment("csharp"), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
    except OSError as exc:
        return {"available": False, "reason": f"OmniSharp start failed: {exc}", "reference_counts": {}}
    responses: "queue.Queue[Dict[str, Any]]" = queue.Queue()
    def reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                value = json.loads(line)
                if isinstance(value, dict): responses.put(value)
            except json.JSONDecodeError:
                continue
    threading.Thread(target=reader, daemon=True).start()
    counts: Dict[str, int] = {}
    try:
        assert proc.stdin is not None
        deadline = time.monotonic() + timeout_seconds
        proc.stdin.write(json.dumps({"Seq": 0, "Type": "request", "Command": "/projects", "Arguments": {}}) + "\n"); proc.stdin.flush()
        while True:
            ready = responses.get(timeout=max(0.1, deadline - time.monotonic()))
            if ready.get("Type") == "response" and ready.get("Request_seq") == 0:
                if not ready.get("Success", False): raise RuntimeError(str(ready.get("Message", "OmniSharp project load failed")))
                break
        for sequence, item in enumerate(candidates, 1):
            source = root / str(item["file"])
            if not source.is_file() or source.suffix.lower() != ".cs": continue
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            line = int(item["line"]) - 1; name = str(item["name"])
            if line < 0 or line >= len(lines) or name not in lines[line]: continue
            request = {"Seq": sequence, "Type": "request", "Command": "/findusages", "Arguments": {"FileName": str(source.resolve()), "Line": line, "Column": lines[line].index(name), "OnlyThisFile": False, "ExcludeDefinition": False}}
            proc.stdin.write(json.dumps(request) + "\n"); proc.stdin.flush()
            while True:
                message = responses.get(timeout=max(0.1, deadline - time.monotonic()))
                if message.get("Type") == "response" and message.get("Request_seq") == sequence:
                    if not message.get("Success", False): raise RuntimeError(str(message.get("Message", "OmniSharp request failed")))
                    body = message.get("Body") or {}
                    locations = body.get("QuickFixes") or body.get("Locations") or []
                    counts[str(item["id"])] = len(locations) if isinstance(locations, list) else 0
                    break
        return {"available": True, "provider": "omnisharp-native", "reference_counts": counts, "timed_out": time.monotonic() >= deadline}
    except (OSError, RuntimeError, TimeoutError, queue.Empty) as exc:
        return {"available": False, "reason": f"OmniSharp reference probe failed: {str(exc) or type(exc).__name__}", "reference_counts": {}}
    finally:
        proc.terminate()

def python_reference_counts(root: Path, candidates: List[Dict[str, Any]], timeout_seconds: float = 45.0, language: str = "python") -> Dict[str, Any]:
    """Ask an optional pyright-compatible server for Python symbol references.

    The bounded result is only used to *remove* candidates that the server can
    prove referenced. A failed or incomplete probe never changes candidates.
    """
    if language == "java":
        argv = _java_server_command(root)
        extensions, language_id = {".java"}, "java"
        if not argv:
            return {"available": False, "reason": "java LSP provider unavailable", "reference_counts": {}}
        command = argv[0]
    else:
        provider = _LANGUAGE_PROVIDERS.get(language)
        if not provider:
            return {"available": False, "reason": f"unsupported LSP language: {language}", "reference_counts": {}}
        environment_name, commands, extensions, language_id = provider
        configured = os.environ.get(environment_name, "").strip()
        command = _provider_command(environment_name, commands)
        if not command or (configured and not Path(command).is_file()):
            return {"available": False, "reason": f"{language} LSP provider unavailable", "reference_counts": {}}
        argv = [command, "-mode=stdio"] if language == "go" else ([command, "--stdio"] if language in {"python", "typescript_javascript", "csharp"} else [command])
    try:
        proc = subprocess.Popen(argv, cwd=str(root), env=_server_environment(language), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
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
            if "method" in item and "id" in item:
                method = str(item["method"])
                request_params = item.get("params") or {}
                result = [{} for _ in request_params.get("items", [])] if method == "workspace/configuration" else None
                response = json.dumps({"jsonrpc":"2.0", "id": item["id"], "result": result}).encode("utf-8")
                assert proc.stdin is not None
                proc.stdin.write(f"Content-Length: {len(response)}\r\n\r\n".encode("ascii") + response); proc.stdin.flush()
                continue
            if item.get("id") == request_id:
                if "error" in item:
                    raise RuntimeError(str(item["error"]))
                return item.get("result")
    try:
        init_params: Dict[str, Any] = {"processId": None, "rootPath": str(root.resolve()), "rootUri": root.resolve().as_uri(), "workspaceFolders": [{"uri": root.resolve().as_uri(), "name": root.name}], "capabilities": {"workspace": {"configuration": True, "workspaceFolders": True}, "textDocument": {"references": {"dynamicRegistration": False}}}}
        if language == "typescript_javascript":
            tsserver = Path(command).parent / "node_modules" / "typescript" / "lib" / "tsserver.js"
            if tsserver.is_file():
                init_params["initializationOptions"] = {"tsserver": {"path": str(tsserver)}}
        elif language == "rust":
            init_params["initializationOptions"] = {
                "cargo": {"features": "all"},
                "linkedProjects": [str(root.resolve() / "Cargo.toml")]
            }
        initialized = request("initialize", init_params, min(45.0 if language == "csharp" else (20.0 if language == "java" else 10.0), timeout_seconds)) or {}
        if not (initialized.get("capabilities") or {}).get("referencesProvider"):
            return {"available": False, "reason": "provider has no references capability", "reference_counts": {}}
        assert proc.stdin is not None
        init = json.dumps({"jsonrpc":"2.0","method":"initialized","params":{}}).encode("utf-8")
        proc.stdin.write(f"Content-Length: {len(init)}\r\n\r\n".encode("ascii") + init); proc.stdin.flush()
        counts: Dict[str, int] = {}
        deadline = time.monotonic() + timeout_seconds
        for item in candidates:
            source = root / str(item["file"]); name = str(item["name"]); line = int(item["line"]) - 1
            if source.suffix not in extensions or not source.is_file() or time.monotonic() >= deadline:
                continue
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
            if line < 0 or line >= len(lines) or name not in lines[line]:
                continue
            uri = source.resolve().as_uri(); column = lines[line].index(name)
            open_payload = json.dumps({"jsonrpc":"2.0","method":"textDocument/didOpen","params":{"textDocument":{"uri":uri,"languageId":language_id,"version":1,"text":"\n".join(lines)}}}).encode("utf-8")
            proc.stdin.write(f"Content-Length: {len(open_payload)}\r\n\r\n".encode("ascii") + open_payload); proc.stdin.flush()
            # Servers build workspace indexes asynchronously; wait briefly within the existing bounded budget.
            time.sleep(min(5.0 if language in {"rust", "csharp"} else 1.0, max(0.0, deadline - time.monotonic())))
            locations = request("textDocument/references", {"textDocument":{"uri":uri},"position":{"line":line,"character":column},"context":{"includeDeclaration":True}}, min(15.0, max(0.5, deadline-time.monotonic()))) or []
            counts[str(item["id"])] = len(locations) if isinstance(locations, list) else 0
        return {"available": True, "reference_counts": counts, "timed_out": time.monotonic() >= deadline}
    except (OSError, RuntimeError, TimeoutError, queue.Empty) as exc:
        return {"available": False, "reason": f"reference probe failed: {str(exc) or type(exc).__name__}", "reference_counts": {}}
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
