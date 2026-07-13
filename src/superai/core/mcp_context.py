"""
MCP-style context packs for external CLI / tool handoff (Phase 8 / I1).

Builds a structured JSON context envelope SuperAI can pass to external CLIs,
and parse envelopes back into SuperAI memory/history.
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


CONTEXT_SCHEMA = "superai.mcp_context.v1"


class MCPContextPack:
    """
    Structured context pack:

    {
      "schema": "superai.mcp_context.v1",
      "id": "...",
      "created_at": "...",
      "task": "...",
      "goal": "...",
      "files": [...],
      "memory_snippets": [...],
      "skills": [...],
      "constraints": [...],
      "metadata": {...}
    }
    """

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root or (Path.home() / ".superai" / "contexts"))
        self.root.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        task: str,
        goal: Optional[str] = None,
        files: Optional[List[str]] = None,
        memory_snippets: Optional[List[Dict[str, Any]]] = None,
        skills: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_memory: bool = True,
        auto_skills: bool = True,
    ) -> Dict[str, Any]:
        mem = list(memory_snippets or [])
        skill_names = list(skills or [])

        if auto_memory and not mem:
            try:
                from .memory_palace import MemoryPalace

                hits = MemoryPalace().query_semantic(task, top_k=5)
                for h in hits:
                    mem.append(
                        {
                            "id": h.get("id"),
                            "content": (h.get("content") or "")[:800],
                            "metadata": h.get("metadata") or {},
                        }
                    )
            except Exception:  # noqa: BLE001
                pass

        if auto_skills and not skill_names:
            try:
                from .skills import SkillsManager

                for s in SkillsManager().get_relevant_skills(task, top_k=3):
                    skill_names.append(s.get("name") or "")
            except Exception:  # noqa: BLE001
                pass

        pack = {
            "schema": CONTEXT_SCHEMA,
            "id": f"ctx-{uuid.uuid4().hex[:12]}",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "task": task,
            "goal": goal or task,
            "files": list(files or []),
            "memory_snippets": mem,
            "skills": [s for s in skill_names if s],
            "constraints": list(constraints or []),
            "metadata": metadata or {},
        }
        return pack

    def save(self, pack: Dict[str, Any], path: Optional[Path] = None) -> Path:
        out = Path(path or (self.root / f"{pack.get('id', 'ctx')}.json"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(pack, indent=2, default=str), encoding="utf-8")
        return out

    def load(self, path: Path) -> Dict[str, Any]:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Context pack must be a JSON object")
        return data

    def format_for_prompt(self, pack: Dict[str, Any], max_chars: int = 4000) -> str:
        """Render pack as text suitable for CLI/LLM prompts."""
        lines = [
            f"[SuperAI Context {pack.get('id')}]",
            f"Goal: {pack.get('goal') or pack.get('task')}",
            f"Task: {pack.get('task')}",
        ]
        if pack.get("constraints"):
            lines.append("Constraints:")
            for c in pack["constraints"]:
                lines.append(f"  - {c}")
        if pack.get("skills"):
            lines.append("Relevant skills: " + ", ".join(pack["skills"]))
        if pack.get("files"):
            lines.append("Files:")
            for f in pack["files"][:20]:
                lines.append(f"  - {f}")
        if pack.get("memory_snippets"):
            lines.append("Memory:")
            for m in pack["memory_snippets"][:5]:
                content = (m.get("content") or "")[:300]
                lines.append(f"  - {content}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            return text[: max_chars - 20] + "\n…[truncated]"
        return text

    def wrap_cli_prompt(self, pack: Dict[str, Any], user_prompt: str) -> str:
        return f"{self.format_for_prompt(pack)}\n\n---\nUser request:\n{user_prompt}"

    def parse_cli_output(
        self,
        stdout: str,
        stderr: str = "",
        exit_code: int = 0,
        cli: str = "unknown",
        context_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Normalize external CLI output into a SuperAI result envelope."""
        return {
            "schema": "superai.cli_result.v1",
            "ok": exit_code == 0,
            "cli": cli,
            "exit_code": exit_code,
            "stdout": (stdout or "")[:20000],
            "stderr": (stderr or "")[:5000],
            "context_id": context_id,
            "parsed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def ingest_to_memory(
        self,
        envelope: Dict[str, Any],
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Store CLI result envelope in Memory Palace."""
        try:
            from .memory_palace import MemoryPalace

            content = (
                f"CLI {envelope.get('cli')} result (ok={envelope.get('ok')}): "
                f"{(envelope.get('stdout') or '')[:1500]}"
            )
            mid = MemoryPalace().store(
                content,
                tags=tags or ["cli", "mcp_context", str(envelope.get("cli") or "ext")],
                metadata={
                    "ok": envelope.get("ok"),
                    "context_id": envelope.get("context_id"),
                    "exit_code": envelope.get("exit_code"),
                },
            )
            return mid
        except Exception:  # noqa: BLE001
            return None
