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
from typing import Any, Dict, List, Optional, Tuple

from .memory_palace import MemoryPalace


class LearningEngine:
    def __init__(self, memory_palace: MemoryPalace):
        self.memory = memory_palace
        self.history_file = os.path.expanduser("~/.superai/learning_history.json")
        self._ensure_history_file()

    def _ensure_history_file(self) -> None:
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        if not os.path.exists(self.history_file):
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def _log_to_history(self, entry: dict) -> None:
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            if not isinstance(history, list):
                history = []
            history.append(entry)
            # Cap file growth
            if len(history) > 5000:
                history = history[-5000:]
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
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

    def _memory_score(self, mem: Dict[str, Any]) -> float:
        """
        Multi-factor keep-score for conflict resolution / distillation.
        Higher = more worth keeping.
        """
        meta = mem.get("metadata") or {}
        imp = float(mem.get("importance") or meta.get("importance") or 0.5)
        success = meta.get("success")
        succ_boost = 0.25 if success is True else (-0.15 if success is False else 0.0)
        # Recency: parse ISO-ish created_at
        recency = 0.0
        created = str(meta.get("created_at") or "")
        try:
            # crude: later timestamps sort higher when compared as strings for ISO
            if created:
                recency = min(0.2, max(0.0, len(created) * 0.001))
                # prefer newer: use year-month if present
                if "T" in created or "-" in created:
                    recency = 0.15
        except Exception:
            pass
        feedback = 0.2 if meta.get("has_human_feedback") else 0.0
        latency = float(meta.get("latency") or 0.0)
        # prefer faster successes slightly
        lat_penalty = min(0.1, latency / 100.0) if success is True else 0.0
        mid = 0.05 if meta.get("phase") == "mid_task" else 0.0
        deprecated = -1.0 if meta.get("deprecated") in (True, "true", 1) else 0.0
        return imp + succ_boost + recency + feedback - lat_penalty + mid + deprecated

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

    def resolve_conflicts(self, auto_resolve: bool = True) -> Dict[str, Any]:
        """
        Resolve conflicts by multi-factor scoring:
        keep highest-scoring memories (prefer successful, important, recent);
        deprecate failures and low-score duplicates more aggressively.
        """
        conflicts = self.detect_conflicts()
        resolved_count = 0
        resolved_details: List[Dict[str, Any]] = []

        if not auto_resolve:
            return {
                "conflicts_found": len(conflicts),
                "conflicts_resolved": 0,
                "resolved_details": [],
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
            # Keep top success if any, else top overall
            keep_candidates = [
                m
                for m in scored
                if (m.get("metadata") or {}).get("success") is True
            ] or scored
            keep = keep_candidates[0]
            keep_score = self._memory_score(keep)
            deprecated_ids = []

            for mem in scored:
                if mem.get("id") == keep.get("id"):
                    continue
                mid = mem.get("id")
                if not mid:
                    continue
                meta = mem.get("metadata") or {}
                score = self._memory_score(mem)
                # Always demote clear failures when a success exists
                is_fail = meta.get("success") is False
                # Keep diverse successes with high score close to keeper
                if (
                    meta.get("success") is True
                    and score >= keep_score * 0.85
                    and self._jaccard(
                        mem.get("content") or "", keep.get("content") or ""
                    )
                    < 0.55
                ):
                    # soft demote only
                    new_imp = max(0.15, float(mem.get("importance") or 0.5) * 0.85)
                    self.memory.update_metadata(
                        mid,
                        {
                            "importance": round(new_imp, 4),
                            "conflict_soft_demote": True,
                        },
                    )
                    continue

                factor = 0.25 if is_fail else 0.45
                new_imp = max(0.05, float(mem.get("importance") or 0.5) * factor)
                ok = self.memory.update_metadata(
                    mid,
                    {
                        "importance": round(new_imp, 4),
                        "deprecated": True,
                        "deprecated_reason": (
                            "Conflict resolve — lower multi-factor score "
                            f"(score={round(score, 3)} vs keep={round(keep_score, 3)})"
                        ),
                        "resolved_into": keep.get("id"),
                        "resolve_method": "multi_factor_score",
                    },
                )
                if ok:
                    resolved_count += 1
                    deprecated_ids.append(mid)

            resolved_details.append(
                {
                    "task_type": conflict["task_type"],
                    "model": conflict["model"],
                    "kept_memory_id": keep.get("id"),
                    "kept_score": round(keep_score, 3),
                    "deprecated_count": len(deprecated_ids),
                    "severity": conflict.get("severity"),
                    "entropy": conflict.get("entropy"),
                }
            )

        return {
            "conflicts_found": len(conflicts),
            "conflicts_resolved": resolved_count,
            "resolved_details": resolved_details,
            "method": "multi_factor_score+entropy",
            "message": (
                f"Resolved {resolved_count} conflicting memories by multi-factor scoring."
                if resolved_count
                else "No conflicts required resolution."
            ),
        }

    def distill_knowledge(
        self,
        task_type: Optional[str] = None,
        min_memories: int = 5,
        similarity_threshold: float = 0.55,
    ) -> Dict[str, Any]:
        """
        Consolidate redundant learnings using Jaccard similarity within groups.
        Writes a consolidated summary memory; deprecates near-duplicates only.
        """
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
                "distilled": False,
                "message": f"Not enough memories to distill (found {len(memories)})",
                "groups_analyzed": 0,
                "groups_distilled": 0,
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

        for key, mem_list in groups.items():
            if len(mem_list) < 4:
                continue
            mem_list.sort(key=lambda x: self._memory_score(x), reverse=True)
            top = mem_list[0]
            # Cluster near-duplicates of top by similarity
            cluster = [top]
            rest_keep = []
            for other in mem_list[1:]:
                sim = self._jaccard(
                    other.get("content") or "", top.get("content") or ""
                )
                # also compare to any already-kept diverse item
                diverse = all(
                    self._jaccard(other.get("content") or "", k.get("content") or "")
                    < similarity_threshold
                    for k in rest_keep
                )
                if sim >= similarity_threshold:
                    cluster.append(other)
                elif diverse and (other.get("metadata") or {}).get("success") is True:
                    rest_keep.append(other)
                else:
                    cluster.append(other)

            if len(cluster) < 2:
                continue

            # Deprecate duplicates in cluster (except top)
            for other in cluster[1:]:
                mid = other.get("id")
                if not mid:
                    continue
                current = float(other.get("importance", 0.5))
                new_imp = max(0.08, current * 0.5)
                ok = self.memory.update_metadata(
                    mid,
                    {
                        "importance": round(new_imp, 4),
                        "consolidated": True,
                        "consolidated_into": top.get("id"),
                        "deprecated": True,
                        "deprecated_reason": (
                            "Distilled near-duplicate "
                            f"(jaccard>={similarity_threshold})"
                        ),
                        "distill_method": "jaccard_cluster",
                    },
                )
                if ok:
                    deprecated_count += 1
                    consolidated_ids.append(mid)

            # Store a consolidated summary memory
            try:
                t_type, model = key
                bullets = []
                for m in cluster[:5]:
                    bullets.append(f"- {(m.get('content') or '')[:220]}")
                summary = (
                    f"Distilled knowledge for {t_type} / {model}\n"
                    f"From {len(cluster)} similar learnings:\n"
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
                        "distilled_from": [top.get("id")] + consolidated_ids[:8],
                        "deprecated": False,
                    },
                    importance=min(
                        1.0, float(top.get("importance") or 0.7) + 0.1
                    ),
                )
                summary_ids.append(sid)
            except Exception:
                pass

            distilled_count += 1

        return {
            "distilled": distilled_count > 0,
            "groups_analyzed": len(groups),
            "groups_distilled": distilled_count,
            "memories_deprecated": deprecated_count,
            "consolidated_memory_ids": consolidated_ids,
            "summary_memory_ids": summary_ids,
            "method": "jaccard_similarity+multi_factor_score",
            "similarity_threshold": similarity_threshold,
            "message": (
                f"Analyzed {len(groups)} groups. Distilled {distilled_count} "
                f"group(s), deprecated {deprecated_count} near-duplicate(s), "
                f"wrote {len(summary_ids)} summary memor(ies)."
            ),
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
