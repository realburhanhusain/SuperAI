"""
Skills System for SuperAI (Phase 4)

Markdown skills under ~/.superai/skills/ with JSON index.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class SkillsManager:
    def __init__(self, skills_dir: Optional[str] = None):
        if skills_dir:
            self.skills_dir = skills_dir
        else:
            self.skills_dir = os.path.expanduser("~/.superai/skills")
        os.makedirs(self.skills_dir, exist_ok=True)
        self.index_file = os.path.join(self.skills_dir, "skills_index.json")
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def _load_index(self) -> Dict:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_index(self, index: Dict) -> None:
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2)

    def create_skill(
        self,
        name: str,
        content: str,
        tags: Optional[List[str]] = None,
        description: str = "",
    ) -> str:
        if tags is None:
            tags = []

        # Idempotent: improve existing auto skills instead of clobbering blindly
        index = self._load_index()
        if name in index:
            self.improve_skill(name, content, reason="auto-update from new successes")
            return os.path.join(self.skills_dir, index[name]["filename"])

        filename = f"{re.sub(r'[^a-zA-Z0-9_-]+', '_', name).strip('_').lower()}.md"
        filepath = os.path.join(self.skills_dir, filename)

        header = (
            f"---\n"
            f"name: {name}\n"
            f"created: {datetime.now().isoformat()}\n"
            f"tags: {tags}\n"
            f"description: {description}\n"
            f"usage_count: 0\n"
            f"last_used: null\n"
            f"---\n\n"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(header + content)

        index[name] = {
            "filename": filename,
            "tags": tags,
            "description": description,
            "created": datetime.now().isoformat(),
            "usage_count": 0,
            "last_used": None,
            "version": 1,
        }
        self._save_index(index)
        return filepath

    def get_skill_content(self, name: str, max_chars: int = 1200) -> Optional[str]:
        index = self._load_index()
        if name not in index:
            return None
        filepath = os.path.join(self.skills_dir, index[name]["filename"])
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        # Drop YAML front matter for prompt injection
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                text = parts[2].strip()
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        return text

    def mark_used(self, name: str) -> None:
        index = self._load_index()
        if name not in index:
            return
        index[name]["usage_count"] = int(index[name].get("usage_count") or 0) + 1
        index[name]["last_used"] = datetime.now().isoformat()
        self._save_index(index)

    def improve_skill(
        self, name: str, new_content_addition: str, reason: str = ""
    ) -> bool:
        index = self._load_index()
        if name not in index:
            return False
        filename = index[name]["filename"]
        filepath = os.path.join(self.skills_dir, filename)
        if not os.path.exists(filepath):
            return False
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n## Improvement ({datetime.now().isoformat()})\n")
            if reason:
                f.write(f"**Reason:** {reason}\n\n")
            f.write(new_content_addition)
        index[name]["version"] = int(index[name].get("version") or 1) + 1
        index[name]["last_improved"] = datetime.now().isoformat()
        self._save_index(index)
        return True

    def list_skills(self) -> List[Dict]:
        index = self._load_index()
        return [{"name": name, **meta} for name, meta in index.items()]

    def record_outcome(self, name: str, success: bool) -> None:
        """Track skill performance (F4.3)."""
        index = self._load_index()
        if name not in index:
            return
        meta = index[name]
        meta["outcomes_total"] = int(meta.get("outcomes_total") or 0) + 1
        if success:
            meta["outcomes_success"] = int(meta.get("outcomes_success") or 0) + 1
        total = max(1, int(meta["outcomes_total"]))
        meta["success_rate"] = round(
            int(meta.get("outcomes_success") or 0) / total, 3
        )
        self._save_index(index)

    def promote_skill(self, name: str) -> bool:
        """Mark skill as promoted after sandbox (F4.1)."""
        index = self._load_index()
        if name not in index:
            return False
        index[name]["status"] = "active"
        index[name]["promoted_at"] = datetime.now().isoformat()
        self._save_index(index)
        return True

    def sandbox_skill(self, name: str) -> bool:
        """Place skill in sandbox status (not injected until promoted)."""
        index = self._load_index()
        if name not in index:
            return False
        index[name]["status"] = "sandbox"
        self._save_index(index)
        return True

    def rollback_skill(self, name: str) -> bool:
        """
        Rollback last improvement by truncating last ## Improvement section (F4.2).
        """
        index = self._load_index()
        if name not in index:
            return False
        filepath = os.path.join(self.skills_dir, index[name]["filename"])
        if not os.path.exists(filepath):
            return False
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        marker = "\n\n## Improvement ("
        idx = text.rfind(marker)
        if idx < 0:
            return False
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text[:idx])
        index[name]["version"] = max(1, int(index[name].get("version") or 1) - 1)
        index[name]["last_rollback"] = datetime.now().isoformat()
        self._save_index(index)
        return True

    def get_relevant_skills(self, task_description: str, top_k: int = 5) -> List[Dict]:
        """Keyword + tag relevance; skip sandbox skills for injection."""
        index = self._load_index()
        results: List[Dict] = []
        task_lower = (task_description or "").lower()
        task_words = {w for w in re.findall(r"[a-z0-9_]+", task_lower) if len(w) > 2}

        for name, meta in index.items():
            if meta.get("status") == "sandbox":
                continue
            score = 0
            tags = meta.get("tags") or []
            for tag in tags:
                tag_l = str(tag).lower()
                if tag_l in task_lower:
                    score += 3
                elif tag_l in task_words:
                    score += 2
            name_words = {w for w in re.findall(r"[a-z0-9_]+", name.lower()) if len(w) > 2}
            score += 2 * len(name_words.intersection(task_words))
            desc = (meta.get("description") or "").lower()
            desc_words = {w for w in re.findall(r"[a-z0-9_]+", desc) if len(w) > 2}
            score += len(desc_words.intersection(task_words))
            score += min(2, int(meta.get("usage_count") or 0) // 5)
            # Prefer higher historical success rate
            sr = meta.get("success_rate")
            if sr is not None:
                score += float(sr)

            if score > 0:
                content = self.get_skill_content(name) or ""
                results.append(
                    {
                        "name": name,
                        "score": score,
                        "description": meta.get("description", ""),
                        "tags": tags,
                        "content": content,
                        "usage_count": meta.get("usage_count", 0),
                        "success_rate": meta.get("success_rate"),
                        "status": meta.get("status", "active"),
                    }
                )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def format_for_prompt(self, skills: List[Dict], max_skills: int = 3) -> str:
        """Build a prompt block from skill dicts (with content)."""
        if not skills:
            return ""
        lines = ["Relevant skills from SuperAI skill library:"]
        for s in skills[:max_skills]:
            body = (s.get("content") or s.get("description") or "").strip()
            lines.append(f"\n### Skill: {s.get('name')}")
            if body:
                lines.append(body)
            else:
                lines.append(s.get("description") or "(no content)")
        return "\n".join(lines)

    def delete_skill(self, name: str) -> bool:
        index = self._load_index()
        if name not in index:
            return False
        filename = index[name].get("filename")
        filepath = os.path.join(self.skills_dir, filename) if filename else None
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        del index[name]
        # Remove from others' deps
        for meta in index.values():
            deps = meta.get("depends_on") or []
            if name in deps:
                meta["depends_on"] = [d for d in deps if d != name]
        self._save_index(index)
        return True

    def set_dependencies(self, name: str, depends_on: List[str]) -> bool:
        index = self._load_index()
        if name not in index:
            return False
        # only keep existing skills
        deps = [d for d in depends_on if d in index and d != name]
        index[name]["depends_on"] = deps
        self._save_index(index)
        return True

    def resolve_dependencies(self, name: str) -> List[str]:
        """Return dependency names in order (deps first), detecting cycles."""
        index = self._load_index()
        seen: List[str] = []
        visiting: set = set()

        def walk(n: str) -> None:
            if n in seen:
                return
            if n in visiting:
                raise ValueError(f"Skill dependency cycle involving {n}")
            if n not in index:
                return
            visiting.add(n)
            for d in index[n].get("depends_on") or []:
                walk(d)
            visiting.discard(n)
            seen.append(n)

        walk(name)
        return seen

    def validate_skill(self, name: str) -> Dict:
        """Lightweight skill test / validation before use."""
        index = self._load_index()
        if name not in index:
            return {"ok": False, "error": f"Unknown skill: {name}"}
        meta = index[name]
        issues: List[str] = []
        content = self.get_skill_content(name, max_chars=5000) or ""
        if len(content.strip()) < 10:
            issues.append("content too short")
        if meta.get("status") == "sandbox":
            issues.append("still in sandbox (promote before production use)")
        try:
            chain = self.resolve_dependencies(name)
        except ValueError as e:
            issues.append(str(e))
            chain = []
        for dep in meta.get("depends_on") or []:
            if dep not in index:
                issues.append(f"missing dependency: {dep}")
        ok = len(issues) == 0
        result = {
            "ok": ok,
            "name": name,
            "version": meta.get("version"),
            "status": meta.get("status", "active"),
            "depends_on": meta.get("depends_on") or [],
            "dependency_order": chain,
            "issues": issues,
            "content_chars": len(content),
        }
        index[name]["last_validated"] = datetime.now().isoformat()
        index[name]["validation_ok"] = ok
        self._save_index(index)
        return result
