"""
LearningEngine — self-learning system for SuperAI (Phase 3).

Single clean implementation (no duplicate methods).
Persists importance/deprecation updates via MemoryPalace.update_metadata.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

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
            }
        )
        return memory_id

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

    def detect_conflicts(self, task_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Flag (task_type, model) groups with mixed success/failure rates.

        Requires >= 3 memories; flags when success rate is between 25% and 75%.
        Also flags any group with both success and failure present (lighter severity).
        """
        memories = self.memory.retrieve_by_tags(["learning"], limit=500)
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
            if len(mem_list) < 3:
                # Still note mixed if both outcomes present (for CLI visibility)
                succ = [m for m in mem_list if m.get("metadata", {}).get("success") is True]
                fail = [m for m in mem_list if m.get("metadata", {}).get("success") is False]
                if succ and fail and len(mem_list) >= 2:
                    rate = len(succ) / len(mem_list)
                    conflicts.append(
                        {
                            "task_type": t_type,
                            "model": model,
                            "total_memories": len(mem_list),
                            "success_count": len(succ),
                            "failure_count": len(fail),
                            "success_rate": round(rate * 100, 1),
                            "severity": "low",
                            "description": (
                                f"Mixed outcomes for '{t_type}' / {model} "
                                f"({len(succ)} ok / {len(fail)} fail) — small sample"
                            ),
                        }
                    )
                continue

            successes = sum(
                1 for m in mem_list if m.get("metadata", {}).get("success") is True
            )
            total = len(mem_list)
            success_rate = successes / total
            if 0.25 < success_rate < 0.75:
                conflicts.append(
                    {
                        "task_type": t_type,
                        "model": model,
                        "total_memories": total,
                        "success_count": successes,
                        "failure_count": total - successes,
                        "success_rate": round(success_rate * 100, 1),
                        "severity": "high" if 0.35 < success_rate < 0.65 else "medium",
                        "description": (
                            f"Model shows inconsistent results on '{t_type}' tasks "
                            f"(success rate: {round(success_rate * 100, 1)}%)"
                        ),
                    }
                )
        return conflicts

    def resolve_conflicts(self, auto_resolve: bool = True) -> Dict[str, Any]:
        """Deprecate lower-importance memories in conflicting groups (persisted)."""
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
            ]
            if len(group) < 2:
                continue

            group.sort(
                key=lambda x: (
                    float(x.get("importance", 0.5)),
                    str((x.get("metadata") or {}).get("created_at", "")),
                ),
                reverse=True,
            )
            keep = group[0]
            deprecated_ids = []
            for mem in group[1:]:
                mid = mem.get("id")
                if not mid:
                    continue
                current_imp = float(mem.get("importance", 0.5))
                new_imp = max(0.05, current_imp * 0.4)
                ok = self.memory.update_metadata(
                    mid,
                    {
                        "importance": round(new_imp, 4),
                        "deprecated": True,
                        "deprecated_reason": "Resolved conflict - lower confidence",
                        "resolved_into": keep.get("id"),
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
                    "deprecated_count": len(deprecated_ids),
                }
            )

        return {
            "conflicts_found": len(conflicts),
            "conflicts_resolved": resolved_count,
            "resolved_details": resolved_details,
            "message": (
                f"Resolved {resolved_count} conflicting memories by deprecation."
                if resolved_count
                else "No conflicts required resolution."
            ),
        }

    def distill_knowledge(
        self, task_type: Optional[str] = None, min_memories: int = 5
    ) -> Dict[str, Any]:
        """Consolidate redundant learnings; persist reduced importance + consolidated flag."""
        tags = ["learning"]
        if task_type:
            tags.append(task_type)
        memories = self.memory.retrieve_by_tags(tags, limit=500)

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

        for key, mem_list in groups.items():
            if len(mem_list) < 4:
                continue
            mem_list.sort(
                key=lambda x: float(x.get("importance", 0.5)), reverse=True
            )
            top = mem_list[0]
            for other in mem_list[1:]:
                mid = other.get("id")
                if not mid:
                    continue
                current = float(other.get("importance", 0.5))
                new_imp = max(0.1, current * 0.6)
                ok = self.memory.update_metadata(
                    mid,
                    {
                        "importance": round(new_imp, 4),
                        "consolidated": True,
                        "consolidated_into": top.get("id"),
                        "deprecated": True,
                        "deprecated_reason": "Distilled into higher-importance learning",
                    },
                )
                if ok:
                    deprecated_count += 1
                    consolidated_ids.append(mid)
            distilled_count += 1

        return {
            "distilled": distilled_count > 0,
            "groups_analyzed": len(groups),
            "groups_distilled": distilled_count,
            "memories_deprecated": deprecated_count,
            "consolidated_memory_ids": consolidated_ids,
            "message": (
                f"Analyzed {len(groups)} groups. Distilled {distilled_count} "
                f"group(s), deprecated {deprecated_count} memory(ies)."
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
    ) -> Dict[str, Any]:
        query = task_description
        if task_type:
            query = f"{task_type} task: {task_description}"

        memories = self.memory.query_semantic(query=query, top_k=limit)
        positive: List[Dict] = []
        warnings: List[Dict] = []

        for mem in memories:
            meta = mem.get("metadata") or {}
            content = (mem.get("content") or "")[:350]
            item = {
                "content": content,
                "model": meta.get("model"),
                "task_type": meta.get("task_type"),
                "id": mem.get("id"),
            }
            if meta.get("success") is True:
                positive.append(item)
            else:
                warnings.append(item)

        return {
            "relevant_learnings": positive,
            "warnings": warnings,
            "total_retrieved": len(memories),
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
