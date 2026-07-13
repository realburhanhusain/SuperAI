"""
Pattern extraction & generalization from learning history (Phase 3 depth).
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


class PatternExtractor:
    def __init__(self, history_path: Optional[Path] = None):
        self.history_path = Path(
            history_path
            or (Path.home() / ".superai" / "learning_history.json")
        )

    def _load(self) -> List[Dict[str, Any]]:
        if not self.history_path.exists():
            return []
        try:
            data = json.loads(self.history_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def extract(self, min_support: int = 2) -> Dict[str, Any]:
        history = self._load()
        by_type: Dict[str, List[Dict]] = defaultdict(list)
        model_success: Dict[str, Counter] = defaultdict(Counter)
        keywords: Counter = Counter()
        failures: List[str] = []

        for h in history:
            tt = str(h.get("task_type") or h.get("type") or "general")
            by_type[tt].append(h)
            model = str(h.get("model_used") or h.get("model") or "unknown")
            ok = bool(h.get("success", h.get("ok", False)))
            model_success[model]["ok" if ok else "fail"] += 1
            text = str(h.get("task_description") or h.get("task") or "")
            for w in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", text.lower()):
                keywords[w] += 1
            if not ok and h.get("error_message"):
                failures.append(str(h["error_message"])[:200])

        # Generalizations: task_type → preferred model
        preferences = []
        for model, ctr in model_success.items():
            total = ctr["ok"] + ctr["fail"]
            if total < min_support:
                continue
            rate = ctr["ok"] / total
            preferences.append(
                {
                    "model": model,
                    "success_rate": round(rate, 3),
                    "n": total,
                }
            )
        preferences.sort(key=lambda x: (-x["success_rate"], -x["n"]))

        type_patterns = []
        for tt, items in by_type.items():
            if len(items) < min_support:
                continue
            succ = sum(1 for i in items if i.get("success") or i.get("ok"))
            models = Counter(
                str(i.get("model_used") or i.get("model") or "?") for i in items
            )
            best_model, _ = models.most_common(1)[0]
            type_patterns.append(
                {
                    "task_type": tt,
                    "count": len(items),
                    "success_rate": round(succ / len(items), 3),
                    "preferred_model": best_model,
                    "generalization": (
                        f"For {tt} tasks, prefer {best_model} "
                        f"(seen {len(items)} times, {succ} successes)."
                    ),
                }
            )

        return {
            "history_size": len(history),
            "model_preferences": preferences[:10],
            "type_patterns": type_patterns,
            "top_keywords": keywords.most_common(15),
            "recent_failure_signatures": failures[-10:],
            "skills_suggested": [
                {
                    "name": f"pattern-{p['task_type']}",
                    "description": p["generalization"],
                }
                for p in type_patterns
                if p["success_rate"] >= 0.6
            ],
        }

    def apply_to_skills(self, min_support: int = 3) -> List[str]:
        """Create/improve skills from strong patterns."""
        from .skills import SkillsManager

        patterns = self.extract(min_support=min_support)
        sm = SkillsManager()
        created = []
        for s in patterns.get("skills_suggested") or []:
            name = s["name"]
            body = (
                f"# Auto pattern skill\n\n{s['description']}\n\n"
                "Apply this preference when the task matches this type."
            )
            sm.create_skill(
                name,
                body,
                tags=["pattern", "auto"],
                description=s["description"][:120],
            )
            created.append(name)
        return created
