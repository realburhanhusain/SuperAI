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
    ):
        self.binary = binary or os.getenv("SUPERAI_BIN") or shutil.which("superai") or "superai"
        self.env = {**os.environ, **(env or {})}
        self.timeout = timeout

    def _run(self, args: List[str]) -> Dict[str, Any]:
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
            return json.loads(text)
        except json.JSONDecodeError:
            for line in reversed(text.splitlines()):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        return json.loads(line)
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
