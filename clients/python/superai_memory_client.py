"""
Thin SuperAI Memory client (Phase 9+).

Default transport: invoke `superai` CLI as subprocess (JSON mode).
Does not open SuperAI database files.

Usage:
  from superai_memory_client import SuperAIMemoryClient
  c = SuperAIMemoryClient()
  print(c.recall("Cloud SQL", strategy="auto"))
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional


class SuperAIMemoryClient:
    def __init__(
        self,
        *,
        binary: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: float = 120.0,
        http_base: Optional[str] = None,
    ):
        self.binary = binary or os.getenv("SUPERAI_BIN") or shutil.which("superai") or "superai"
        self.env = {**os.environ, **(env or {})}
        self.timeout = timeout
        # P9-R4: optional HTTP JSON when SUPERAI_HTTP_BASE is set / passed
        self.http_base = (
            (http_base or os.getenv("SUPERAI_HTTP_BASE") or "").strip().rstrip("/")
            or None
        )

    def _run_http(self, path: str, *, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        import urllib.error
        import urllib.parse
        import urllib.request

        assert self.http_base
        q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
        url = f"{self.http_base}{path}" + (f"?{q}" if q else "")
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "superai-memory-client/0.1"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body)
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "error": str(e)[:300],
                "error_code": "http",
                "transport": "http",
                "url": url,
            }

    def _run(self, args: List[str]) -> Dict[str, Any]:
        # Prefer HTTP for a few stable endpoints when configured
        if self.http_base and args:
            if args[0] == "recall" and len(args) >= 2:
                # recall QUERY --strategy S --top-k N
                q = args[1]
                strategy = "auto"
                top_k = 10
                if "--strategy" in args:
                    i = args.index("--strategy")
                    if i + 1 < len(args):
                        strategy = args[i + 1]
                if "--top-k" in args:
                    i = args.index("--top-k")
                    if i + 1 < len(args):
                        top_k = args[i + 1]
                out = self._run_http(
                    "/v1/memory/recall",
                    params={"q": q, "strategy": strategy, "top_k": top_k},
                )
                out.setdefault("transport", "http")
                return out
            if args[0:2] == ["cloud", "status"]:
                out = self._run_http("/v1/memory/cloud/status")
                out.setdefault("transport", "http")
                return out

        cmd = [self.binary, "--json", *args]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self.env,
                check=False,
            )
        except FileNotFoundError:
            return {
                "ok": False,
                "error": f"superai binary not found: {self.binary}",
                "error_code": "not_found",
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout", "error_code": "timeout"}
        text = (proc.stdout or "").strip()
        if not text:
            return {
                "ok": proc.returncode == 0,
                "error": (proc.stderr or "")[:400] or "empty stdout",
                "exit_code": proc.returncode,
            }
        # last JSON object line if mixed
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data.setdefault("transport", "cli")
            return data
        except json.JSONDecodeError:
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data = json.loads(line)
                        if isinstance(data, dict):
                            data.setdefault("transport", "cli")
                        return data
                    except json.JSONDecodeError:
                        continue
            return {
                "ok": False,
                "error": "non-json output",
                "raw": text[:500],
                "exit_code": proc.returncode,
            }

    def recall(self, query: str, *, strategy: str = "auto", top_k: int = 10) -> Dict[str, Any]:
        return self._run(["recall", query, "--strategy", strategy, "--top-k", str(top_k)])

    def cognify(self, source: str, *, mode: str = "mock", dataset: str = "default") -> Dict[str, Any]:
        return self._run(["cognify", source, "--mode", mode, "--dataset", dataset])

    def kg_status(self) -> Dict[str, Any]:
        return self._run(["kg", "status"])

    def dataset_list(self) -> Dict[str, Any]:
        return self._run(["dataset", "list"])

    def memory_eval(self) -> Dict[str, Any]:
        return self._run(["memory-eval"])

    def otel_status(self) -> Dict[str, Any]:
        return self._run(["otel", "status"])

    def cloud_status(self) -> Dict[str, Any]:
        return self._run(["cloud", "status"])

    def host_hook_emit(self, event: str, content: str = "", session: Optional[str] = None) -> Dict[str, Any]:
        args = ["host-hook", "emit", event]
        if content:
            args += ["--content", content]
        if session:
            args += ["--session", session]
        return self._run(args)
