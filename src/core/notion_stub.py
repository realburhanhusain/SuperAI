"""
Notion integration stub (Future Plan G10).

Uses Notion API when NOTION_API_KEY + NOTION_DATABASE_ID / page id set;
otherwise dry-run / local log.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


class NotionClient:
    def __init__(self, dry_run: Optional[bool] = None):
        self.api_key = (os.getenv("NOTION_API_KEY") or "").strip()
        self.database_id = (os.getenv("NOTION_DATABASE_ID") or "").strip()
        if dry_run is None:
            dry_run = not bool(self.api_key)
        self.dry_run = dry_run
        self.log_path = Path.home() / ".superai" / "notion_log.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def capabilities(self) -> Dict[str, Any]:
        return {
            "api_key_set": bool(self.api_key),
            "database_id_set": bool(self.database_id),
            "dry_run": self.dry_run,
        }

    def _log(self, entry: Dict[str, Any]) -> None:
        entry = {**entry, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def write_page(
        self,
        title: str,
        content: str,
        database_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = database_id or self.database_id
        payload = {
            "parent": {"database_id": db} if db else {"type": "page_id", "page_id": "dry"},
            "properties": {
                "Name": {
                    "title": [{"text": {"content": title[:200]}}]
                }
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content[:1900]}}]
                    },
                }
            ],
        }
        if self.dry_run or not self.api_key:
            self._log({"action": "write_page", "dry_run": True, "title": title, "content": content[:200]})
            return {"ok": True, "dry_run": True, "title": title}

        req = urllib.request.Request(
            "https://api.notion.com/v1/pages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            self._log({"action": "write_page", "ok": True, "id": data.get("id")})
            return {"ok": True, "id": data.get("id"), "url": data.get("url")}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")[:400]
            return {"ok": False, "error": f"HTTP {e.code}: {err}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def search(self, query: str) -> Dict[str, Any]:
        if self.dry_run or not self.api_key:
            self._log({"action": "search", "dry_run": True, "query": query})
            return {
                "ok": True,
                "dry_run": True,
                "results": [{"title": f"(stub) {query}", "id": None}],
            }
        body = json.dumps({"query": query, "page_size": 10}).encode("utf-8")
        req = urllib.request.Request(
            "https://api.notion.com/v1/search",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            for r in data.get("results") or []:
                results.append({"id": r.get("id"), "object": r.get("object")})
            return {"ok": True, "results": results}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}
