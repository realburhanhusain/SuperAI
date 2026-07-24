"""
LearningEngine — self-learning system for SuperAI (Phase 3).

- learn_from_task / learn_from_step (mid-task)
- refresh_context_mid_task for dynamic injection during runs
- conflict detect/resolve with multi-factor scoring
- distillation with similarity + consolidated summary memory
Wings/rooms assigned via MemoryPalace.store metadata (first-class).
"""

from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .memory_palace import MemoryPalace


class LearningEngine:
    def __init__(self, memory_palace: MemoryPalace):
        self.memory = memory_palace
        self.history_file = os.path.expanduser("~/.superai/learning_history.json")
        self._ensure_history_file()

    def embedding_backend_info(self) -> Dict[str, Any]:
        """
        Honest embedding backend for Memory Palace / learning similarity.

        Hash embeddings are always available offline but are **not** a real
        semantic model — conflict clustering and distill near-dup detection
        are weaker than sentence-transformers / EmbeddingGemma.
        """
        emb_id = str(getattr(self.memory, "embedding_id", "") or "unknown")
        prefer_hash = (os.getenv("SUPERAI_EMBEDDING_HASH") or "").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        is_hash = (
            prefer_hash
            or "hash" in emb_id.lower()
            or emb_id.lower() in {"superai-hash-embedding", "hashembeddingfunction"}
        )
        try:
            import sentence_transformers  # noqa: F401

            st_installed = True
        except ImportError:
            st_installed = False
        quality = "lexical_hash" if is_hash else "semantic_model"
        note = (
            "Hash embeddings active (no sentence-transformers / model load). "
            "Conflict detect is success-entropy (not vector); distill near-dup "
            "uses Jaccard unless a real embedding model is installed. "
            "Install: pip install 'superai[embeddings]' or sentence-transformers; "
            "unset SUPERAI_EMBEDDING_HASH to enable."
            if is_hash
            else f"Semantic embeddings active ({emb_id})."
        )
        return {
            "embedding_id": emb_id,
            "is_hash": is_hash,
            "sentence_transformers_installed": st_installed,
            "quality": quality,
            "affects": [
                "memory_palace_semantic_search",
                "memory_clustering",
                "learning_distill_near_dup",
            ],
            "does_not_affect": [
                "conflict_detect_entropy",  # success-rate based
                "multi_factor_keep_score",
            ],
            "message": note,
        }

    def _cosine(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)) or 1.0
        nb = math.sqrt(sum(x * x for x in b)) or 1.0
        return max(0.0, min(1.0, dot / (na * nb)))

    def _content_similarity(self, a: str, b: str) -> Tuple[float, str]:
        """
        Similarity for distill near-dup.

        Prefer real embeddings when palace is not on hash backend; else Jaccard.
        Returns (score, method).
        """
        info = self.embedding_backend_info()
        if not info.get("is_hash"):
            try:
                fn = getattr(self.memory, "embedding_function", None)
                if fn is not None:
                    va, vb = fn([a or "", b or ""])
                    return self._cosine(list(va), list(vb)), "embedding_cosine"
            except Exception:
                pass
        return self._jaccard(a, b), "jaccard"

    def _ensure_history_file(self) -> None:
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _log_to_history(self, entry: dict) -> None:
        try:
            from .store_lock import atomic_write_json, store_lock

            hist_path = Path(self.history_file)
            root = hist_path.parent
            with store_lock(root, name="learning_history.lock", timeout=30.0):
                history: list = []
                if hist_path.exists():
                    try:
                        history = json.loads(
                            hist_path.read_text(encoding="utf-8")
                        )
                    except Exception:
                        history = []
                if not isinstance(history, list):
                    history = []
                history.append(entry)
                if len(history) > 5000:
                    history = history[-5000:]
                atomic_write_json(hist_path, history)
        except Exception as e:  # noqa: BLE001
            print(f"Warning: Could not write to learning history: {e}")

    def learn_from_task(
        self,
        task_description: str,
        task_type: str,
        model_used: str,
        success: bool,
        latency: float,
        cost: float = 0.0,
        steps_completed: int = 0,
        error_message: Optional[str] = None,
        human_feedback: Optional[str] = None,
        steps_failed: int = 0,
    ) -> str:
        """Store a learning from a completed task outcome."""
        importance = 0.7 if success else 0.9
        if human_feedback:
            importance = 1.0
        if steps_failed and not success:
            importance = min(1.0, importance + 0.05)

        content = (
            f"Task: {task_description}\n"
            f"Type: {task_type}\n"
            f"Model: {model_used}\n"
            f"Success: {success}\n"
            f"Latency: {latency}s | Cost: ${cost}\n"
            f"Steps completed: {steps_completed}"
        )
        if steps_failed:
            content += f" | Steps failed: {steps_failed}"
        content += "\n"
        if error_message:
            content += f"Error: {error_message}\n"
        if human_feedback:
            content += f"Human Feedback: {human_feedback}\n"

        tags = ["learning", task_type or "general", model_used or "unknown"]
        tags.append("success" if success else "failure")

        metadata = {
            "task_type": task_type or "general",
            "model": model_used or "unknown",
            "success": bool(success),
            "latency": float(latency),
            "cost": float(cost),
            "steps_completed": int(steps_completed),
            "steps_failed": int(steps_failed),
            "has_human_feedback": bool(human_feedback),
            "deprecated": False,
            "source": "learning_engine",
            "phase": "task_end",
        }

        memory_id = self.memory.store(
            content=content,
            tags=tags,
            metadata=metadata,
            importance=importance,
        )

        self._log_to_history(
            {
                "memory_id": memory_id,
                "timestamp": datetime.now().isoformat(),
                "task_description": task_description,
                "task_type": task_type,
                "model": model_used,
                "success": success,
                "latency": latency,
                "cost": cost,
                "steps_failed": steps_failed,
                "human_feedback": human_feedback,
                "phase": "task_end",
            }
        )
        # Wings & Rooms: MemoryPalace.store assigns wing/room from metadata (reliable core path)
        return memory_id

    def learn_from_step(
        self,
        task_description: str,
        step_id: int,
        step_description: str,
        *,
        task_type: str = "general",
        model_used: str = "unknown",
        success: bool = True,
        output: str = "",
        error: Optional[str] = None,
        latency: float = 0.0,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Mid-task learning — store a step outcome while the run is still in progress.
        Used by the orchestrator for dynamic adaptation (not only pre/post task).
        """
        importance = 0.55 if success else 0.85
        content = (
            f"[mid-task step {step_id}] {step_description}\n"
            f"Parent task: {task_description[:400]}\n"
            f"Type: {task_type} | Model: {model_used} | Success: {success}\n"
        )
        if output:
            content += f"Output: {output[:600]}\n"
        if error:
            content += f"Error: {error[:400]}\n"
        tags = [
            "learning",
            "mid_task",
            task_type or "general",
            model_used or "unknown",
            "success" if success else "failure",
            f"step:{step_id}",
        ]
        metadata = {
            "task_type": task_type or "general",
            "model": model_used or "unknown",
            "success": bool(success),
            "latency": float(latency),
            "step_id": int(step_id),
            "task_id": task_id,
            "phase": "mid_task",
            "source": "learning_engine_step",
            "deprecated": False,
        }
        memory_id = self.memory.store(
            content=content,
            tags=tags,
            metadata=metadata,
            importance=importance,
        )
        self._log_to_history(
            {
                "memory_id": memory_id,
                "timestamp": datetime.now().isoformat(),
                "phase": "mid_task",
                "step_id": step_id,
                "task_description": task_description[:300],
                "step_description": step_description[:200],
                "success": success,
                "model": model_used,
                "task_id": task_id,
            }
        )
        return memory_id

    def refresh_context_mid_task(
        self,
        task_description: str,
        *,
        task_type: Optional[str] = None,
        recent_step_outputs: Optional[List[str]] = None,
        limit: int = 6,
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dynamic context injection during execution.

        Blends semantic retrieval with recent step text so later steps adapt
        to what already happened in this run (not only pre-task learnings).
        """
        recent = list(recent_step_outputs or [])
        query_parts = [task_description]
        if task_type:
            query_parts.insert(0, f"{task_type} task")
        if recent:
            query_parts.append("Recent steps: " + " | ".join(r[:200] for r in recent[-3:]))
        query = "\n".join(query_parts)

        base = self.get_relevant_context_for_current_task(
            task_description=query,
            task_type=task_type,
            limit=limit,
            wing=wing,
            room=room,
        )
        # Prefer mid-task memories for this task when available
        mid_hits = []
        try:
            mid_hits = self.memory.query_semantic(
                query=task_description,
                top_k=max(3, limit // 2),
                tags=["mid_task"],
                wing=wing,
                room=room,
            )
        except Exception:
            mid_hits = []

        mid_items = []
        for h in mid_hits or []:
            meta = h.get("metadata") or {}
            mid_items.append(
                {
                    "content": (h.get("content") or "")[:350],
                    "model": meta.get("model"),
                    "task_type": meta.get("task_type"),
                    "id": h.get("id"),
                    "phase": "mid_task",
                    "step_id": meta.get("step_id"),
                    "success": meta.get("success"),
                }
            )

        # Live run buffer (not yet in palace)
        live = [
            {"content": f"[this run] {t[:300]}", "phase": "live_buffer"}
            for t in recent[-4:]
            if t
        ]

        learnings = list(base.get("relevant_learnings") or [])
        # Prepend mid-task + live so adaptation is visible first
        merged = mid_items + live + learnings
        # de-dupe by content prefix
        seen = set()
        unique = []
        for item in merged:
            key = (item.get("content") or "")[:80]
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return {
            "relevant_learnings": unique[:limit],
            "warnings": base.get("warnings") or [],
            "mid_task_count": len(mid_items),
            "live_buffer_count": len(live),
            "total_retrieved": len(unique),
            "query": query[:500],
            "message": "Mid-task adaptive context (live steps + palace learnings).",
            "adapted": True,
        }

    def get_learnings_summary(self, task_type: Optional[str] = None) -> Dict[str, Any]:
        tags = ["learning"]
        if task_type:
            tags.append(task_type)
        memories = self.memory.retrieve_by_tags(tags, limit=200)
        total = len(memories)
        successes = sum(
            1 for m in memories if m.get("metadata", {}).get("success") is True
        )
        failures = sum(
            1 for m in memories if m.get("metadata", {}).get("success") is False
        )
        # Unclear success flag counts as neither
        return {
            "total_learnings": total,
            "success_count": successes,
            "failure_count": failures if failures else max(0, total - successes),
            "success_rate": round((successes / total * 100), 1) if total > 0 else 0.0,
        }

    @staticmethod
    def _binary_entropy(p: float) -> float:
        """Entropy of Bernoulli(p); max 1.0 at p=0.5."""
        p = min(1.0, max(0.0, float(p)))
        if p <= 0.0 or p >= 1.0:
            return 0.0
        return float(-(p * math.log2(p) + (1 - p) * math.log2(1 - p)))

    @staticmethod
    def _token_set(text: str) -> set:
        return {
            t
            for t in re.split(r"\W+", (text or "").lower())
            if len(t) > 2
        }

    @classmethod
    def _jaccard(cls, a: str, b: str) -> float:
        sa, sb = cls._token_set(a), cls._token_set(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / max(1, len(sa | sb))

    def _memory_score_breakdown(self, mem: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-factor keep-score breakdown for conflict resolution / distillation.
        Higher total = more worth keeping. Used for CLI explainability.
        """
        meta = mem.get("metadata") or {}
        imp = float(mem.get("importance") or meta.get("importance") or 0.5)
        success = meta.get("success")
        succ_boost = 0.25 if success is True else (-0.15 if success is False else 0.0)
        recency = 0.0
        created = str(meta.get("created_at") or "")
        try:
            if created:
                recency = min(0.2, max(0.0, len(created) * 0.001))
                if "T" in created or "-" in created:
                    recency = 0.15
        except Exception:
            pass
        feedback = 0.2 if meta.get("has_human_feedback") else 0.0
        latency = float(meta.get("latency") or 0.0)
        lat_penalty = min(0.1, latency / 100.0) if success is True else 0.0
        mid = 0.05 if meta.get("phase") == "mid_task" else 0.0
        deprecated = -1.0 if meta.get("deprecated") in (True, "true", 1) else 0.0
        total = imp + succ_boost + recency + feedback - lat_penalty + mid + deprecated
        return {
            "score": round(total, 4),
            "importance": round(imp, 4),
            "success_boost": succ_boost,
            "success": success,
            "recency": round(recency, 4),
            "human_feedback": feedback,
            "latency_penalty": round(lat_penalty, 4),
            "mid_task": mid,
            "deprecated_penalty": deprecated,
        }

    def _memory_score(self, mem: Dict[str, Any]) -> float:
        """Multi-factor keep-score (higher = more worth keeping)."""
        return float(self._memory_score_breakdown(mem)["score"])

    def _get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Best-effort fetch by id (MemoryPalace has no dedicated get())."""
        mid = str(memory_id or "")
        if not mid:
            return None
        if hasattr(self.memory, "get"):
            try:
                got = self.memory.get(mid)
                if got:
                    return got
            except Exception:
                pass
        try:
            for m in self.memory.get_all_memories() or []:
                if str(m.get("id") or "") == mid:
                    return m
        except Exception:
            pass
        return None

    def _apply_learning_update(
        self,
        memory_id: str,
        *,
        metadata: Dict[str, Any],
        tags: Optional[List[str]] = None,
        content: Optional[str] = None,
    ) -> bool:
        """
        In-place update for lifecycle flags. Prefer update_metadata (no re-store
        duplicates). Best-effort tag merge on local backends.
        """
        mid = str(memory_id)
        ok = False
        try:
            if hasattr(self.memory, "update") and tags is not None:
                try:
                    self.memory.update(mid, metadata=metadata, tags=tags)
                    return True
                except Exception:
                    pass
            if hasattr(self.memory, "update_metadata"):
                ok = bool(self.memory.update_metadata(mid, metadata))
            # Best-effort tags on in-memory / faiss docs
            if tags is not None:
                try:
                    if getattr(self.memory, "use_faiss", False) and getattr(
                        self.memory, "faiss_store", None
                    ):
                        doc = self.memory.faiss_store.docs.get(mid)
                        if doc is not None:
                            doc["tags"] = list(tags)
                            meta = dict(doc.get("metadata") or {})
                            meta.update(metadata)
                            doc["metadata"] = meta
                            if "importance" in metadata:
                                doc["importance"] = metadata["importance"]
                            self.memory.faiss_store.docs[mid] = doc
                            try:
                                self.memory.faiss_store.save()
                            except Exception:
                                pass
                            ok = True
                    for mem in getattr(self.memory, "memories", None) or []:
                        if str(mem.get("id") or "") == mid:
                            mem["tags"] = list(tags)
                            meta = mem.setdefault("metadata", {})
                            meta.update(metadata)
                            if "importance" in metadata:
                                mem["importance"] = metadata["importance"]
                            ok = True
                            break
                except Exception:
                    pass
            return ok
        except Exception:
            return False

    def detect_conflicts(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Flag (task_type, model) groups with unstable outcomes.

        Uses success-rate entropy (not only fixed 25–75% bands) plus mixed-sample rules.
        """
        memories = self.memory.retrieve_by_tags(["learning"], limit=500)
        memories = [
            m
            for m in memories
            if (m.get("metadata") or {}).get("deprecated") not in (True, "true", 1)
        ]
        if task_type:
            memories = [
                m
                for m in memories
                if (m.get("metadata") or {}).get("task_type") == task_type
            ]

        groups: Dict[tuple, List[Dict]] = {}
        for mem in memories:
            meta = mem.get("metadata") or {}
            t_type = meta.get("task_type") or "unknown"
            model = meta.get("model") or "unknown"
            groups.setdefault((t_type, model), []).append(mem)

        conflicts: List[Dict[str, Any]] = []
        for (t_type, model), mem_list in groups.items():
            succ = [
                m for m in mem_list if m.get("metadata", {}).get("success") is True
            ]
            fail = [
                m for m in mem_list if m.get("metadata", {}).get("success") is False
            ]
            total = len(mem_list)
            if total < 2 or not (succ and fail):
                continue

            rate = len(succ) / total
            entropy = self._binary_entropy(rate)
            # Severity from entropy + sample size
            if entropy >= 0.9 and total >= 4:
                severity = "high"
            elif entropy >= 0.7 or (0.25 < rate < 0.75 and total >= 3):
                severity = "medium"
            else:
                severity = "low"

            # Skip low severity with tiny samples only if nearly pure
            if severity == "low" and total < 3 and entropy < 0.5:
                continue

            # Latency instability signal
            lats = [
                float((m.get("metadata") or {}).get("latency") or 0)
                for m in mem_list
            ]
            lat_var = 0.0
            if len(lats) >= 2:
                mean = sum(lats) / len(lats)
                lat_var = sum((x - mean) ** 2 for x in lats) / len(lats)

            # Sample snippets + scores for Conflict UI (M062)
            samples = []
            for m in sorted(mem_list, key=lambda x: self._memory_score(x), reverse=True)[
                :5
            ]:
                br = self._memory_score_breakdown(m)
                samples.append(
                    {
                        "id": m.get("id"),
                        "success": (m.get("metadata") or {}).get("success"),
                        "importance": (m.get("metadata") or {}).get(
                            "importance", m.get("importance")
                        ),
                        "score": br["score"],
                        "score_factors": {
                            k: br[k]
                            for k in (
                                "importance",
                                "success_boost",
                                "recency",
                                "human_feedback",
                                "latency_penalty",
                            )
                        },
                        "preview": str(m.get("content") or "")[:120],
                    }
                )
            top_id = samples[0]["id"] if samples else None
            conflicts.append(
                {
                    "task_type": t_type,
                    "model": model,
                    "total_memories": total,
                    "success_count": len(succ),
                    "failure_count": len(fail),
                    "success_rate": round(rate * 100, 1),
                    "entropy": round(entropy, 3),
                    "latency_variance": round(lat_var, 4),
                    "severity": severity,
                    "suggested_keep_id": top_id,
                    "samples": samples,
                    "description": (
                        f"Inconsistent '{t_type}' / {model}: "
                        f"{len(succ)} ok / {len(fail)} fail "
                        f"(rate={round(rate * 100, 1)}%, H={round(entropy, 2)})"
                    ),
                }
            )
        # High severity first
        order = {"high": 0, "medium": 1, "low": 2}
        conflicts.sort(key=lambda c: (order.get(c["severity"], 9), -c["entropy"]))
        return conflicts

    def promote_durable(
        self,
        memory_id: Optional[str] = None,
        *,
        min_importance: float = 0.75,
        limit: int = 20,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Promote high-value learnings to durable patterns (V6 M061).

        In-place: sets metadata.durable + durable tag + importance boost.
        dry_run: preview eligible/skipped without mutating.
        """
        promoted: List[str] = []
        candidates_out: List[Dict[str, Any]] = []
        skipped: List[Dict[str, Any]] = []
        not_found = False

        if memory_id:
            m = self._get_memory(memory_id)
            if not m:
                return {
                    "ok": False,
                    "promoted": [],
                    "count": 0,
                    "min_importance": min_importance,
                    "dry_run": dry_run,
                    "not_found": True,
                    "memory_id": memory_id,
                    "candidates": [],
                    "skipped": [
                        {
                            "id": memory_id,
                            "eligible": False,
                            "reason": "id_not_found",
                        }
                    ],
                    "product": "learning.promote_durable",
                    "message": f"Memory id not found: {memory_id}",
                }
            pool = [m]
        else:
            try:
                pool = self.memory.retrieve_by_tags(["learning"], limit=200)
            except Exception:
                pool = []
            # Prefer non-deprecated, non-already-durable when scanning
            pool = [
                m
                for m in pool
                if not self._is_deprecated(m)
            ]

        cap = max(1, int(limit))
        for mem in pool:
            mid = str(mem.get("id") or "")
            if not mid:
                continue
            meta = dict(mem.get("metadata") or {})
            imp = float(meta.get("importance") or mem.get("importance") or 0.5)
            success = meta.get("success")
            already = self._is_durable(mem)

            reason = "eligible"
            eligible = True
            if already:
                eligible = False
                reason = "already_durable"
            elif self._is_deprecated(mem):
                eligible = False
                reason = "deprecated"
            elif memory_id is None and imp < min_importance:
                eligible = False
                reason = f"below_min_importance ({imp:.3f} < {min_importance})"
            elif memory_id is None and success is False:
                eligible = False
                reason = "failed_outcome"

            row = {
                "id": mid,
                "eligible": eligible,
                "reason": reason,
                "importance": round(imp, 4),
                "success": success,
                "task_type": meta.get("task_type"),
                "model": meta.get("model"),
                "already_durable": already,
                "preview": str(mem.get("content") or "")[:120],
            }

            if not eligible:
                if len(skipped) < 40:
                    skipped.append(row)
                continue

            if memory_id is None and len(promoted) >= cap:
                if len(skipped) < 40:
                    skipped.append({**row, "reason": "over_limit"})
                continue

            candidates_out.append(row)
            if dry_run:
                promoted.append(mid)
                continue

            new_imp = max(imp, min(1.0, imp + 0.1))
            meta["durable"] = True
            meta["promoted_at"] = datetime.now().isoformat()
            meta["importance"] = new_imp
            tags = list(mem.get("tags") or [])
            if "durable" not in tags:
                tags.append("durable")
            ok = self._apply_learning_update(mid, metadata=meta, tags=tags)
            if not ok:
                try:
                    ok = bool(
                        self.memory.update_metadata(
                            mid,
                            {
                                "durable": True,
                                "promoted_at": meta["promoted_at"],
                                "importance": new_imp,
                            },
                        )
                    )
                except Exception:
                    ok = False
            if ok:
                promoted.append(mid)
            else:
                skipped.append({**row, "eligible": False, "reason": "update_failed"})

        msg = (
            f"{'Would promote' if dry_run else 'Promoted'} {len(promoted)} learning(s) "
            f"to durable (min_importance={min_importance}"
            f"{', dry_run' if dry_run else ''})."
        )
        return {
            "ok": True,
            "promoted": [] if dry_run else list(promoted),
            "would_promote": list(promoted) if dry_run else list(promoted),
            "count": len(promoted),
            "min_importance": min_importance,
            "dry_run": dry_run,
            "candidates": candidates_out,
            "skipped": skipped,
            "product": "learning.promote_durable",
            "message": msg,
        }

    def deprecate_memory(self, memory_id: str, reason: str = "deprecated") -> Dict[str, Any]:
        """Mark a memory deprecated (V6 M063 companion). Rows are retained."""
        try:
            mem = self._get_memory(memory_id)
            if not mem:
                return {
                    "ok": False,
                    "memory_id": memory_id,
                    "deprecated": False,
                    "not_found": True,
                    "error": "id_not_found",
                    "product": "learning.deprecate",
                    "message": f"Memory id not found: {memory_id}",
                }
            meta = dict(mem.get("metadata") or {})
            meta["deprecated"] = True
            meta["deprecate_reason"] = reason
            meta["deprecated_reason"] = reason
            meta["deprecated_at"] = datetime.now().isoformat()
            tags = list(mem.get("tags") or [])
            if "deprecated" not in tags:
                tags.append("deprecated")
            ok = self._apply_learning_update(memory_id, metadata=meta, tags=tags)
            if not ok and hasattr(self.memory, "update_metadata"):
                ok = bool(self.memory.update_metadata(memory_id, meta))
            return {
                "ok": bool(ok),
                "memory_id": memory_id,
                "deprecated": bool(ok),
                "reason": reason,
                "deletes_rows": False,
                "product": "learning.deprecate",
                "message": (
                    f"Deprecated {memory_id} (row retained)."
                    if ok
                    else f"Failed to deprecate {memory_id}."
                ),
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e)[:200],
                "memory_id": memory_id,
                "product": "learning.deprecate",
            }

    def undeprecate_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Soft restore a deprecated learning (clear deprecated flags/tags).
        Does not restore pre-deprecate importance.
        """
        mem = self._get_memory(memory_id)
        if not mem:
            return {
                "ok": False,
                "memory_id": memory_id,
                "not_found": True,
                "product": "learning.undeprecate",
                "message": f"Memory id not found: {memory_id}",
            }
        meta = dict(mem.get("metadata") or {})
        meta["deprecated"] = False
        meta.pop("deprecate_reason", None)
        meta.pop("deprecated_reason", None)
        meta["undeprecated_at"] = datetime.now().isoformat()
        tags = [t for t in (mem.get("tags") or []) if str(t).lower() != "deprecated"]
        ok = self._apply_learning_update(memory_id, metadata=meta, tags=tags)
        if not ok and hasattr(self.memory, "update_metadata"):
            ok = bool(
                self.memory.update_metadata(
                    memory_id,
                    {
                        "deprecated": False,
                        "undeprecated_at": meta["undeprecated_at"],
                    },
                )
            )
        return {
            "ok": bool(ok),
            "memory_id": memory_id,
            "deprecated": False,
            "product": "learning.undeprecate",
            "message": (
                f"Undeprecated {memory_id}."
                if ok
                else f"Failed to undeprecate {memory_id}."
            ),
        }

    def _is_learning(self, mem: Dict[str, Any]) -> bool:
        tags = [str(t).lower() for t in (mem.get("tags") or [])]
        meta = mem.get("metadata") or {}
        if "learning" in tags or "distilled" in tags or "durable" in tags:
            return True
        src = str(meta.get("source") or "")
        return src.startswith("learning") or meta.get("task_type") is not None

    def _is_deprecated(self, mem: Dict[str, Any]) -> bool:
        meta = mem.get("metadata") or {}
        if meta.get("deprecated") in (True, "true", 1):
            return True
        tags = [str(t).lower() for t in (mem.get("tags") or [])]
        return "deprecated" in tags

    def _is_durable(self, mem: Dict[str, Any]) -> bool:
        meta = mem.get("metadata") or {}
        if meta.get("durable") in (True, "true", 1):
            return True
        tags = [str(t).lower() for t in (mem.get("tags") or [])]
        return "durable" in tags

    def lifecycle_status(self) -> Dict[str, Any]:
        """
        Product dashboard for learning lifecycle (M061–M063 UX).

        Buckets: active, durable, deprecated, distilled, conflict_groups.
        """
        try:
            mems = self.memory.get_all_memories() or []
        except Exception:
            mems = []
        learnings = [m for m in mems if self._is_learning(m)]
        durable = [m for m in learnings if self._is_durable(m) and not self._is_deprecated(m)]
        deprecated = [m for m in learnings if self._is_deprecated(m)]
        distilled = [
            m
            for m in learnings
            if "distilled" in [str(t).lower() for t in (m.get("tags") or [])]
            or (m.get("metadata") or {}).get("source") == "learning_engine_distill"
        ]
        active = [
            m
            for m in learnings
            if not self._is_deprecated(m) and not self._is_durable(m)
        ]
        conflicts = self.detect_conflicts()
        emb = self.embedding_backend_info()
        return {
            "ok": True,
            "product": "learning.lifecycle_status",
            "total_learnings": len(learnings),
            "active": len(active),
            "durable": len(durable),
            "deprecated": len(deprecated),
            "distilled_summaries": len(distilled),
            "conflict_groups": len(conflicts),
            "buckets": {
                "active": len(active),
                "durable": len(durable),
                "deprecated": len(deprecated),
                "distilled": len(distilled),
            },
            "embedding": emb,
            "top_durable": [
                {
                    "id": m.get("id"),
                    "importance": (m.get("metadata") or {}).get("importance", m.get("importance")),
                    "task_type": (m.get("metadata") or {}).get("task_type"),
                    "preview": str(m.get("content") or "")[:160],
                }
                for m in durable[:5]
            ],
            "message": (
                f"{len(learnings)} learnings — "
                f"{len(durable)} durable, {len(active)} active, "
                f"{len(deprecated)} deprecated, {len(conflicts)} conflict group(s); "
                f"embeddings={emb.get('quality')}"
            ),
            "honesty": {
                "conflict_resolve": "deprecates lower multi-factor scores; does not delete rows",
                "distill": "requires enough similar learnings; may no-op with clear message",
                "embeddings": emb.get("message"),
            },
        }

    def list_lifecycle(
        self,
        kind: str = "active",
        *,
        limit: int = 20,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List learnings by lifecycle kind: active | durable | deprecated | distilled | all."""
        kind_n = (kind or "active").strip().lower()
        try:
            mems = self.memory.get_all_memories() or []
        except Exception:
            mems = []
        learnings = [m for m in mems if self._is_learning(m)]
        if task_type:
            learnings = [
                m
                for m in learnings
                if str((m.get("metadata") or {}).get("task_type") or "") == task_type
            ]

        def _match(m: Dict[str, Any]) -> bool:
            if kind_n == "all":
                return True
            if kind_n == "durable":
                return self._is_durable(m) and not self._is_deprecated(m)
            if kind_n == "deprecated":
                return self._is_deprecated(m)
            if kind_n == "distilled":
                tags = [str(t).lower() for t in (m.get("tags") or [])]
                return "distilled" in tags or (m.get("metadata") or {}).get("source") == "learning_engine_distill"
            # active default
            return not self._is_deprecated(m) and not self._is_durable(m)

        rows = [m for m in learnings if _match(m)]
        rows.sort(
            key=lambda m: float(
                (m.get("metadata") or {}).get("importance") or m.get("importance") or 0
            ),
            reverse=True,
        )
        items = []
        for m in rows[: max(1, limit)]:
            meta = m.get("metadata") or {}
            items.append(
                {
                    "id": m.get("id"),
                    "lifecycle": (
                        "deprecated"
                        if self._is_deprecated(m)
                        else "durable"
                        if self._is_durable(m)
                        else "distilled"
                        if "distilled" in [str(t).lower() for t in (m.get("tags") or [])]
                        else "active"
                    ),
                    "importance": meta.get("importance", m.get("importance")),
                    "task_type": meta.get("task_type"),
                    "model": meta.get("model"),
                    "success": meta.get("success"),
                    "preview": str(m.get("content") or "")[:200],
                }
            )
        return {
            "ok": True,
            "product": "learning.list_lifecycle",
            "kind": kind_n,
            "count": len(items),
            "total_matching": len(rows),
            "items": items,
        }

    def resolve_conflicts(
        self,
        auto_resolve: bool = True,
        *,
        keep_memory_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolve conflicts by multi-factor scoring:
        keep highest-scoring memories (prefer successful, important, recent);
        **deprecate** failures and low-score duplicates (does **not** delete rows).

        keep_memory_id: optional operator override — prefer this id as keeper when
        present in a conflict group.
        """
        conflicts = self.detect_conflicts(task_type=task_type)
        resolved_count = 0
        soft_demoted_count = 0
        resolved_details: List[Dict[str, Any]] = []
        emb = self.embedding_backend_info()

        if not auto_resolve:
            return {
                "ok": True,
                "conflicts_found": len(conflicts),
                "conflicts": conflicts,
                "conflicts_resolved": 0,
                "resolved_details": [],
                "deletes_rows": False,
                "action": "list_only",
                "embedding": emb,
                "product": "learning.resolve_conflicts",
                "message": "Auto-resolve disabled; conflicts listed only.",
            }

        for conflict in conflicts:
            memories = self.memory.retrieve_by_tags(["learning"], limit=500)
            group = [
                m
                for m in memories
                if (m.get("metadata") or {}).get("task_type") == conflict["task_type"]
                and (m.get("metadata") or {}).get("model") == conflict["model"]
                and (m.get("metadata") or {}).get("deprecated") not in (True, "true", 1)
            ]
            if len(group) < 2:
                continue

            scored = sorted(
                group, key=lambda m: self._memory_score(m), reverse=True
            )
            keep_candidates = [
                m
                for m in scored
                if (m.get("metadata") or {}).get("success") is True
            ] or scored
            keep = keep_candidates[0]
            keep_override = False
            if keep_memory_id:
                forced = next(
                    (m for m in scored if str(m.get("id")) == str(keep_memory_id)),
                    None,
                )
                if forced is not None:
                    keep = forced
                    keep_override = True
            keep_breakdown = self._memory_score_breakdown(keep)
            keep_score = float(keep_breakdown["score"])
            deprecated_ids: List[str] = []
            soft_ids: List[str] = []

            for mem in scored:
                if mem.get("id") == keep.get("id"):
                    continue
                mid = mem.get("id")
                if not mid:
                    continue
                meta = mem.get("metadata") or {}
                breakdown = self._memory_score_breakdown(mem)
                score = float(breakdown["score"])
                is_fail = meta.get("success") is False
                if (
                    meta.get("success") is True
                    and score >= keep_score * 0.85
                    and self._jaccard(
                        mem.get("content") or "", keep.get("content") or ""
                    )
                    < 0.55
                ):
                    new_imp = max(0.15, float(mem.get("importance") or 0.5) * 0.85)
                    self.memory.update_metadata(
                        mid,
                        {
                            "importance": round(new_imp, 4),
                            "conflict_soft_demote": True,
                        },
                    )
                    soft_demoted_count += 1
                    soft_ids.append(str(mid))
                    continue

                factor = 0.25 if is_fail else 0.45
                new_imp = max(0.05, float(mem.get("importance") or 0.5) * factor)
                reason = (
                    "Conflict resolve — lower multi-factor score "
                    f"(score={round(score, 3)} vs keep={round(keep_score, 3)}); "
                    "row kept, marked deprecated"
                )
                dep = self.deprecate_memory(str(mid), reason=reason)
                ok = bool(dep.get("ok"))
                if not ok:
                    ok = self.memory.update_metadata(
                        mid,
                        {
                            "importance": round(new_imp, 4),
                            "deprecated": True,
                            "deprecated_reason": reason,
                            "resolved_into": keep.get("id"),
                            "resolve_method": "multi_factor_score",
                        },
                    )
                else:
                    self.memory.update_metadata(
                        mid,
                        {
                            "importance": round(new_imp, 4),
                            "resolved_into": keep.get("id"),
                            "resolve_method": "multi_factor_score",
                        },
                    )
                if ok:
                    resolved_count += 1
                    deprecated_ids.append(str(mid))

            resolved_details.append(
                {
                    "task_type": conflict["task_type"],
                    "model": conflict["model"],
                    "kept_memory_id": keep.get("id"),
                    "kept_score": round(keep_score, 3),
                    "kept_score_factors": keep_breakdown,
                    "keep_override": keep_override,
                    "deprecated_count": len(deprecated_ids),
                    "deprecated_ids": deprecated_ids,
                    "soft_demoted_ids": soft_ids,
                    "soft_demoted_count": len(soft_ids),
                    "severity": conflict.get("severity"),
                    "entropy": conflict.get("entropy"),
                }
            )

        return {
            "ok": True,
            "conflicts_found": len(conflicts),
            "conflicts_resolved": resolved_count,
            "soft_demoted": soft_demoted_count,
            "resolved_details": resolved_details,
            "method": "multi_factor_score+entropy",
            "deletes_rows": False,
            "action": "deprecate_metadata_only",
            "embedding": emb,
            "product": "learning.resolve_conflicts",
            "message": (
                f"Deprecated {resolved_count} lower-score conflicting memories "
                f"(rows retained; not deleted); soft-demoted {soft_demoted_count} "
                f"diverse success(es) via multi-factor scoring."
                if resolved_count or soft_demoted_count
                else "No conflicts required resolution."
            ),
        }

    def distill_knowledge(
        self,
        task_type: Optional[str] = None,
        min_memories: int = 5,
        similarity_threshold: float = 0.55,
        *,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Consolidate redundant learnings using content similarity within groups.

        - Uses **embedding cosine** when palace is not on hash backend
        - Falls back to **Jaccard** (lexical) under hash embeddings
        - Writes a consolidated summary memory; deprecates near-duplicates only
          (does not delete rows)
        - dry_run: preview groups / would-deprecate without mutating
        - No-ops with a clear message when not enough memories / clusters
        """
        emb = self.embedding_backend_info()
        tags = ["learning"]
        if task_type:
            tags.append(task_type)
        memories = self.memory.retrieve_by_tags(tags, limit=500)
        memories = [
            m
            for m in memories
            if (m.get("metadata") or {}).get("deprecated") not in (True, "true", 1)
        ]

        if len(memories) < min_memories:
            return {
                "ok": True,
                "distilled": False,
                "noop": True,
                "noop_reason": "insufficient_memories",
                "message": (
                    f"Not enough memories to distill "
                    f"(found {len(memories)}, need >= {min_memories}). "
                    "Add more learnings or lower --min-memories."
                ),
                "groups_analyzed": 0,
                "groups_distilled": 0,
                "min_memories": min_memories,
                "similarity_threshold": similarity_threshold,
                "dry_run": dry_run,
                "preview_groups": [],
                "embedding": emb,
                "deletes_rows": False,
                "product": "learning.distill",
            }

        groups: Dict[tuple, List[Dict]] = {}
        for mem in memories:
            meta = mem.get("metadata") or {}
            key = (meta.get("task_type", "unknown"), meta.get("model", "unknown"))
            groups.setdefault(key, []).append(mem)

        distilled_count = 0
        consolidated_ids: List[str] = []
        deprecated_count = 0
        summary_ids: List[str] = []
        sim_method_used = "jaccard"
        skipped_small_groups = 0
        preview_groups: List[Dict[str, Any]] = []

        for key, mem_list in groups.items():
            if len(mem_list) < 4:
                skipped_small_groups += 1
                continue
            mem_list.sort(key=lambda x: self._memory_score(x), reverse=True)
            top = mem_list[0]
            cluster = [top]
            rest_keep = []
            for other in mem_list[1:]:
                sim, sim_method_used = self._content_similarity(
                    other.get("content") or "", top.get("content") or ""
                )
                diverse = True
                for k in rest_keep:
                    dsim, _ = self._content_similarity(
                        other.get("content") or "", k.get("content") or ""
                    )
                    if dsim >= similarity_threshold:
                        diverse = False
                        break
                if sim >= similarity_threshold:
                    cluster.append(other)
                elif diverse and (other.get("metadata") or {}).get("success") is True:
                    rest_keep.append(other)
                else:
                    cluster.append(other)

            if len(cluster) < 2:
                continue

            would_deprecate = [
                str(o.get("id")) for o in cluster[1:] if o.get("id")
            ]
            preview_groups.append(
                {
                    "task_type": key[0],
                    "model": key[1],
                    "cluster_size": len(cluster),
                    "keep_id": top.get("id"),
                    "would_deprecate_ids": would_deprecate,
                    "similarity_method": sim_method_used,
                    "similarity_threshold": similarity_threshold,
                }
            )

            if dry_run:
                distilled_count += 1
                deprecated_count += len(would_deprecate)
                consolidated_ids.extend(would_deprecate)
                continue

            for other in cluster[1:]:
                mid = other.get("id")
                if not mid:
                    continue
                current = float(other.get("importance", 0.5))
                new_imp = max(0.08, current * 0.5)
                reason = (
                    f"Distilled near-duplicate ({sim_method_used}>={similarity_threshold}); "
                    "row kept, marked deprecated"
                )
                dep = self.deprecate_memory(str(mid), reason=reason)
                ok = bool(dep.get("ok"))
                self.memory.update_metadata(
                    mid,
                    {
                        "importance": round(new_imp, 4),
                        "consolidated": True,
                        "consolidated_into": top.get("id"),
                        "distill_method": f"{sim_method_used}_cluster",
                    },
                )
                if ok:
                    deprecated_count += 1
                    consolidated_ids.append(mid)

            try:
                t_type, model = key
                bullets = []
                for m in cluster[:5]:
                    bullets.append(f"- {(m.get('content') or '')[:220]}")
                summary = (
                    f"Distilled knowledge for {t_type} / {model}\n"
                    f"From {len(cluster)} similar learnings "
                    f"(similarity={sim_method_used}):\n"
                    + "\n".join(bullets)
                )
                sid = self.memory.store(
                    summary,
                    tags=["learning", "distilled", str(t_type), str(model), "success"],
                    metadata={
                        "task_type": t_type,
                        "model": model,
                        "success": True,
                        "source": "learning_engine_distill",
                        "phase": "distill",
                        "distilled_from": [top.get("id")]
                        + [x for x in consolidated_ids if x][:8],
                        "deprecated": False,
                        "similarity_method": sim_method_used,
                    },
                    importance=min(
                        1.0, float(top.get("importance") or 0.7) + 0.1
                    ),
                )
                summary_ids.append(sid)
            except Exception:
                pass

            distilled_count += 1

        noop = distilled_count == 0
        if noop:
            msg = (
                f"No distillable clusters (analyzed {len(groups)} group(s); "
                f"{skipped_small_groups} group(s) had <4 members). "
                "Need enough similar learnings per (task_type, model)."
            )
        elif dry_run:
            msg = (
                f"[dry-run] Would distill {distilled_count} group(s), "
                f"deprecate {deprecated_count} near-duplicate(s) via "
                f"{sim_method_used} (threshold={similarity_threshold}); "
                f"embedding={emb.get('quality')}. No mutations applied."
            )
        else:
            msg = (
                f"Analyzed {len(groups)} groups. Distilled {distilled_count} "
                f"group(s), deprecated {deprecated_count} near-duplicate(s) "
                f"(rows retained), wrote {len(summary_ids)} summary memor(ies) "
                f"via {sim_method_used}; embedding={emb.get('quality')}."
            )

        return {
            "ok": True,
            "distilled": distilled_count > 0 and not dry_run,
            "noop": noop,
            "noop_reason": "no_similar_clusters" if noop else None,
            "groups_analyzed": len(groups),
            "groups_distilled": distilled_count,
            "groups_skipped_small": skipped_small_groups,
            "memories_deprecated": 0 if dry_run else deprecated_count,
            "would_deprecate_count": deprecated_count if dry_run else deprecated_count,
            "consolidated_memory_ids": [] if dry_run else consolidated_ids,
            "would_deprecate_ids": consolidated_ids if dry_run else [],
            "summary_memory_ids": [] if dry_run else summary_ids,
            "preview_groups": preview_groups,
            "method": f"{sim_method_used}+multi_factor_score",
            "similarity_threshold": similarity_threshold,
            "similarity_method": sim_method_used,
            "dry_run": dry_run,
            "deletes_rows": False,
            "embedding": emb,
            "product": "learning.distill",
            "message": msg,
        }

    def reflect(self) -> Dict[str, Any]:
        """Structured reflection: counts, conflicts, decay, insights."""
        summary = self.get_learnings_summary()
        conflicts = self.detect_conflicts()
        decayed = self.apply_long_term_decay()

        patterns: List[str] = []
        if summary["success_count"] > 3:
            patterns.append("Multiple successful outcomes — effective patterns forming.")
        if summary["failure_count"] > 2:
            patterns.append("Several failures observed — review models/task types.")
        if conflicts:
            patterns.append(
                f"{len(conflicts)} conflict group(s) — consider `superai conflicts --resolve`."
            )

        return {
            "timestamp": datetime.now().isoformat(),
            "total_learnings": summary["total_learnings"],
            "success_count": summary["success_count"],
            "failure_count": summary["failure_count"],
            "success_rate": summary["success_rate"],
            "conflicts_detected": len(conflicts),
            "conflicts_summary": conflicts[:5],
            "memories_decayed": decayed,
            "patterns_identified": patterns,
            "insights": patterns,
            "recommendation": (
                "Run more tasks to strengthen learning patterns."
                if summary["total_learnings"] < 10
                else "Good learning volume. Review conflicts if any."
            ),
            "message": "Reflection completed. System continues to evolve its knowledge.",
        }

    def get_relevant_context_for_current_task(
        self,
        task_description: str,
        task_type: Optional[str] = None,
        limit: int = 6,
        wing: Optional[str] = None,
        room: Optional[str] = None,
    ) -> Dict[str, Any]:
        query = task_description
        if task_type:
            query = f"{task_type} task: {task_description}"

        memories = self.memory.query_semantic(
            query=query, top_k=limit, wing=wing, room=room
        )
        positive: List[Dict] = []
        warnings: List[Dict] = []

        for mem in memories:
            meta = mem.get("metadata") or {}
            if meta.get("deprecated") in (True, "true", 1):
                continue
            content = (mem.get("content") or "")[:350]
            item = {
                "content": content,
                "model": meta.get("model"),
                "task_type": meta.get("task_type"),
                "id": mem.get("id"),
                "wing": meta.get("wing"),
                "room": meta.get("room"),
                "phase": meta.get("phase"),
                "score": round(self._memory_score(mem), 3),
            }
            if meta.get("success") is True:
                positive.append(item)
            else:
                warnings.append(item)

        # Prefer higher multi-factor scores
        positive.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        warnings.sort(key=lambda x: float(x.get("score") or 0), reverse=True)

        return {
            "relevant_learnings": positive,
            "warnings": warnings,
            "total_retrieved": len(memories),
            "wing": wing,
            "room": room,
            "message": "Use these past experiences to guide the current task.",
        }

    def get_recommendations(self, task_type: str, limit: int = 5) -> List[Dict]:
        memories = self.memory.query_semantic(
            query=f"successful {task_type} tasks",
            top_k=limit,
            tags=["success", task_type],
        )
        recommendations = []
        for mem in memories:
            meta = mem.get("metadata") or {}
            recommendations.append(
                {
                    "model": meta.get("model"),
                    "success_rate": "High" if meta.get("success") else "Low",
                    "avg_latency": meta.get("latency"),
                    "content": (mem.get("content") or "")[:200],
                }
            )
        return recommendations

    def apply_long_term_decay(self, decay_factor: float = 0.97) -> int:
        return self.memory.apply_memory_decay(decay_factor=decay_factor)

    def track_knowledge_evolution(self, topic: str, limit: int = 50) -> Dict[str, Any]:
        """
        Track how understanding of a topic evolved over time (F3.5).
        """
        memories = self.memory.retrieve_by_tags(["learning"], limit=200)
        topic_l = (topic or "").lower()
        topic_memories = []
        for m in memories:
            content = (m.get("content") or "").lower()
            meta = m.get("metadata") or {}
            blob = f"{content} {meta}"
            if topic_l in blob:
                topic_memories.append(m)

        if len(topic_memories) < 2:
            return {
                "topic": topic,
                "evolution_detected": False,
                "total_memories": len(topic_memories),
                "message": "Not enough data to track evolution for this topic.",
                "timeline": [],
            }

        def _ts(m: Dict) -> str:
            meta = m.get("metadata") or {}
            return str(meta.get("created_at") or "")

        topic_memories.sort(key=_ts)
        timeline = []
        for mem in topic_memories[:limit]:
            meta = mem.get("metadata") or {}
            timeline.append(
                {
                    "id": mem.get("id"),
                    "timestamp": meta.get("created_at"),
                    "model": meta.get("model"),
                    "success": meta.get("success"),
                    "importance": mem.get("importance", meta.get("importance")),
                    "key_insight": (mem.get("content") or "")[:180],
                    "deprecated": meta.get("deprecated"),
                }
            )

        successes = sum(1 for t in timeline if t.get("success") is True)
        failures = sum(1 for t in timeline if t.get("success") is False)
        return {
            "topic": topic,
            "evolution_detected": True,
            "total_memories": len(topic_memories),
            "success_count": successes,
            "failure_count": failures,
            "timeline": timeline,
            "message": (
                f"Knowledge about '{topic}' spans {len(topic_memories)} memories "
                f"({successes} success / {failures} failure)."
            ),
        }

    def record_human_feedback(
        self,
        task_id: str,
        feedback: str,
        success: Optional[bool] = None,
        task_description: str = "",
        task_type: str = "general",
        model_used: str = "unknown",
    ) -> str:
        """
        Store human feedback as a high-importance learning (F3.3).

        If task history is available, callers may pass richer description/model.
        """
        return self.learn_from_task(
            task_description=task_description or f"Human feedback for task {task_id}",
            task_type=task_type,
            model_used=model_used,
            success=True if success is None else success,
            latency=0.0,
            cost=0.0,
            steps_completed=0,
            human_feedback=f"[task_id={task_id}] {feedback}",
        )

    def create_skills_from_learnings(self, min_success_count: int = 3) -> List[str]:
        """Auto-create skills from repeated successful patterns (Phase 4 hook)."""
        from .skills import SkillsManager

        skills_manager = SkillsManager()
        memories = self.memory.retrieve_by_tags(["success"], limit=100)
        by_task_type: Dict[str, List] = {}
        for mem in memories:
            meta = mem.get("metadata") or {}
            t = meta.get("task_type", "general")
            by_task_type.setdefault(t, []).append(mem)

        created: List[str] = []
        for task_type, mems in by_task_type.items():
            if len(mems) < min_success_count:
                continue
            content = f"# Best Practices for {task_type.title()}\n\n"
            content += "Based on multiple successful executions:\n\n"
            for mem in mems[:5]:
                content += f"- {(mem.get('content') or '')[:300]}\n"
            skill_name = f"Best Practices - {task_type.title()}"
            try:
                skills_manager.create_skill(
                    name=skill_name,
                    content=content,
                    tags=["auto-generated", task_type, "best-practices"],
                    description=f"Auto-generated from {len(mems)} successful {task_type} tasks",
                )
                created.append(skill_name)
            except Exception as e:  # noqa: BLE001
                print(f"Warning: Could not create skill {skill_name}: {e}")
        return created
