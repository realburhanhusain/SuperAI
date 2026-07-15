"""
Centralized Memory Palace for all SuperAI-mediated AIs.

Design:
  - One store: MemoryPalace (~/.superai/memory)
  - READ: inject relevant memories into prompts / CLI context packs
  - WRITE: learn_from_task + store result envelopes after every mediated run
  - Opt-out: config central_memory=false, SUPERAI_CENTRAL_MEMORY=0,
             or use_memory=False / with_context=False on specific calls

External AIs never open the DB directly — SuperAI injects text context and
writes outcomes back so multi-CLI / multi-model / council / terminals share
the same long-term memory when run *through* SuperAI.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def _env_flag(name: str) -> Optional[bool]:
    raw = (os.getenv(name) or "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def central_memory_enabled() -> bool:
    """Master switch for Memory Palace mediation."""
    env = _env_flag("SUPERAI_CENTRAL_MEMORY")
    if env is not None:
        return env
    try:
        from .config import Config

        return bool(Config().get("central_memory", True))
    except Exception:
        return True


def central_memory_write_back_enabled() -> bool:
    env = _env_flag("SUPERAI_CENTRAL_MEMORY_WRITE")
    if env is not None:
        return env
    try:
        from .config import Config

        return bool(Config().get("central_memory_write_back", True))
    except Exception:
        return True


def inject_context(
    task: str,
    *,
    prompt: Optional[str] = None,
    use_memory: Optional[bool] = None,
    use_skills: bool = True,
    goal: Optional[str] = None,
    constraints: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build Memory Palace–backed context and wrap the user prompt.

    Returns:
      {
        enabled, context_id, pack, prompt (possibly wrapped),
        memory_count, skills
      }
    """
    enabled = central_memory_enabled() if use_memory is None else bool(use_memory)
    user_prompt = prompt if prompt is not None else task
    if not enabled:
        return {
            "enabled": False,
            "context_id": None,
            "pack": None,
            "prompt": user_prompt,
            "memory_count": 0,
            "skills": [],
        }

    try:
        from .mcp_context import MCPContextPack

        packer = MCPContextPack()
        pack = packer.build(
            task=task,
            goal=goal or task,
            constraints=constraints,
            metadata={**(metadata or {}), "source": "central_memory"},
            auto_memory=True,
            auto_skills=use_skills,
        )
        wrapped = packer.wrap_cli_prompt(pack, user_prompt)
        return {
            "enabled": True,
            "context_id": pack.get("id"),
            "pack": pack,
            "prompt": wrapped,
            "memory_count": len(pack.get("memory_snippets") or []),
            "skills": list(pack.get("skills") or []),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "enabled": False,
            "context_id": None,
            "pack": None,
            "prompt": user_prompt,
            "memory_count": 0,
            "skills": [],
            "error": str(e),
        }


def memory_preface_for_llm(
    task: str,
    *,
    use_memory: Optional[bool] = None,
    top_k: int = 5,
    max_chars: int = 2500,
) -> str:
    """
    Compact memory block for internal model prompts (council, agentic, chat).
    Empty string if disabled or no hits.
    """
    enabled = central_memory_enabled() if use_memory is None else bool(use_memory)
    if not enabled:
        return ""
    try:
        from .memory_palace import get_shared_palace

        hits = get_shared_palace().query_semantic(task, top_k=top_k)
        if not hits:
            return ""
        lines = ["[SuperAI Memory Palace — shared context]"]
        for h in hits:
            content = (h.get("content") or "")[:400].replace("\n", " ")
            lines.append(f"- {content}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            return text[: max_chars - 20] + "\n…[truncated]"
        return text
    except Exception:
        return ""


def write_back(
    *,
    task: str,
    source: str,
    model_or_cli: str,
    success: bool,
    latency: float = 0.0,
    cost: float = 0.0,
    output: str = "",
    error: Optional[str] = None,
    context_id: Optional[str] = None,
    task_type: str = "general",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    use_memory: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Persist outcome into Memory Palace for future SuperAI-mediated AIs.

    Always-on when central_memory_write_back is enabled (default True).
    """
    enabled = (
        central_memory_write_back_enabled()
        if use_memory is None
        else bool(use_memory)
    )
    if not enabled or not central_memory_enabled():
        return {"ok": False, "skipped": True, "reason": "central_memory_disabled"}

    result: Dict[str, Any] = {"ok": True, "learning_id": None, "ingest_id": None}
    try:
        from .learning_engine import LearningEngine
        from .memory_palace import MemoryPalace

        from .memory_palace import get_shared_palace

        le = LearningEngine(get_shared_palace())
        learning_id = le.learn_from_task(
            task_description=f"[{source}] {task[:500]}",
            task_type=task_type,
            model_used=model_or_cli,
            success=success,
            latency=float(latency or 0),
            cost=float(cost or 0),
            steps_completed=1 if success else 0,
            steps_failed=0 if success else 1,
            error_message=error,
        )
        result["learning_id"] = learning_id
    except Exception as e:  # noqa: BLE001
        result["learning_error"] = str(e)

    # Also store a richer result snippet for semantic recall
    if output or error:
        try:
            from .mcp_context import MCPContextPack

            envelope = MCPContextPack().parse_cli_output(
                stdout=output or "",
                stderr=error or "",
                exit_code=0 if success else 1,
                cli=model_or_cli,
                context_id=context_id,
            )
            tag_list = list(tags or [])
            tag_list.extend(["central_memory", source, model_or_cli])
            mid = MCPContextPack().ingest_to_memory(envelope, tags=tag_list)
            result["ingest_id"] = mid
            # Enrich metadata if store supports it — best effort via second store
            if metadata:
                try:
                    from .memory_palace import get_shared_palace

                    snippet = (
                        f"Source={source} model={model_or_cli} task={task[:300]}\n"
                        f"Success={success}\n"
                        f"Output: {(output or '')[:1200]}"
                    )
                    get_shared_palace().store(
                        snippet,
                        tags=tag_list + ["outcome"],
                        metadata={
                            "source": source,
                            "model": model_or_cli,
                            "success": success,
                            "context_id": context_id,
                            **{k: v for k, v in (metadata or {}).items() if v is not None},
                        },
                    )
                except Exception:
                    pass
        except Exception as e:  # noqa: BLE001
            result["ingest_error"] = str(e)

    return result


def write_back_workflow(
    *,
    task: str,
    source: str,
    workflow_id: str,
    succeeded: int,
    failed: int,
    total: int,
    synthesis: Optional[str] = None,
    jobs: Optional[List[Dict[str, Any]]] = None,
    use_memory: Optional[bool] = None,
) -> Dict[str, Any]:
    """Write a multi-worker (CLI pool / terminal pool) summary into Memory Palace."""
    enabled = (
        central_memory_write_back_enabled()
        if use_memory is None
        else bool(use_memory)
    )
    if not enabled or not central_memory_enabled():
        return {"ok": False, "skipped": True}

    lines = [
        f"Workflow {workflow_id} ({source}): {succeeded}/{total} ok, {failed} failed.",
        f"Task: {task[:800]}",
    ]
    if synthesis:
        lines.append(f"Synthesis: {synthesis[:2000]}")
    for j in (jobs or [])[:12]:
        label = j.get("cli") or j.get("title") or j.get("role") or j.get("id")
        status = j.get("status")
        tail = (j.get("stdout_tail") or j.get("error") or "")[:300]
        lines.append(f"- {label} [{status}]: {tail}")

    blob = "\n".join(lines)
    return write_back(
        task=task,
        source=source,
        model_or_cli=f"workflow:{workflow_id}",
        success=failed == 0 and total > 0,
        latency=0.0,
        output=blob,
        error=None if failed == 0 else f"{failed} workers failed",
        context_id=workflow_id,
        task_type="agentic",
        tags=["workflow", source, "multi_ai"],
        metadata={
            "workflow_id": workflow_id,
            "succeeded": succeeded,
            "failed": failed,
            "total": total,
        },
        use_memory=True,
    )


def status() -> Dict[str, Any]:
    """Dashboard / doctor snippet for central memory."""
    enabled = central_memory_enabled()
    write = central_memory_write_back_enabled()
    stats: Dict[str, Any] = {}
    try:
        from .memory_palace import get_shared_palace

        mp = get_shared_palace()
        all_m = mp.get_all_memories() if hasattr(mp, "get_all_memories") else []
        stats = {
            "count": len(all_m) if isinstance(all_m, list) else None,
            "path": getattr(mp, "persist_directory", None),
            "embedding": getattr(mp, "embedding_id", None),
            "concurrent_safe": True,
        }
    except Exception as e:  # noqa: BLE001
        stats = {"error": str(e)}
    return {
        "enabled": enabled,
        "write_back": write,
        "store": "MemoryPalace",
        "role": "centralized_memory_for_superai_mediated_ais",
        "stats": stats,
        "opt_out": [
            "config central_memory=false",
            "SUPERAI_CENTRAL_MEMORY=0",
            "SUPERAI_CENTRAL_MEMORY_WRITE=0",
            "CLI: --no-memory / --no-context",
        ],
    }
