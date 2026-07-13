"""
Ecosystem integrations (Phase 8 / I6).

- Outbound webhooks for n8n / Zapier / Make
- Search tool stubs (Tavily / Brave / DuckDuckGo)
- Cloud CLI detection (gcloud, aws, az)
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


class EcosystemHub:
    """Lightweight integrations hub — no heavy SDKs required."""

    def __init__(self, dry_run: Optional[bool] = None):
        if dry_run is None:
            dry_run = _env("SUPERAI_ECOSYSTEM_DRY_RUN").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self.dry_run = dry_run

    # ── Webhooks (n8n / Zapier / Make) ─────────────────────────────────

    def webhook_url(self) -> Optional[str]:
        return (
            _env("SUPERAI_N8N_WEBHOOK_URL")
            or _env("SUPERAI_ZAPIER_WEBHOOK_URL")
            or _env("SUPERAI_MAKE_WEBHOOK_URL")
            or _env("SUPERAI_ECOSYSTEM_WEBHOOK_URL")
            or None
        )

    def emit_event(
        self,
        event: str,
        payload: Optional[Dict[str, Any]] = None,
        url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """POST an event JSON to configured automation webhook."""
        target = url or self.webhook_url()
        body = {
            "source": "superai",
            "event": event,
            "payload": payload or {},
        }
        if not target:
            return {
                "ok": False,
                "error": "No webhook URL (SUPERAI_N8N_WEBHOOK_URL / ZAPIER / MAKE)",
                "body": body,
            }
        if self.dry_run:
            return {"ok": True, "dry_run": True, "url": target, "body": body}

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            target,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                return {
                    "ok": True,
                    "status": resp.status,
                    "response": raw[:500],
                    "event": event,
                }
        except urllib.error.HTTPError as e:
            return {"ok": False, "error": f"HTTP {e.code}", "event": event}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e), "event": event}

    # ── Search stubs ───────────────────────────────────────────────────

    def search(
        self,
        query: str,
        provider: str = "auto",
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """
        Web search via Tavily / Brave if keys present; else offline stub.
        """
        provider = (provider or "auto").lower()
        if provider == "auto":
            if _env("TAVILY_API_KEY"):
                provider = "tavily"
            elif _env("BRAVE_API_KEY"):
                provider = "brave"
            else:
                provider = "stub"

        if provider == "tavily" and _env("TAVILY_API_KEY") and not self.dry_run:
            return self._search_tavily(query, max_results)
        if provider == "brave" and _env("BRAVE_API_KEY") and not self.dry_run:
            return self._search_brave(query, max_results)

        # Stub / dry-run results
        return {
            "ok": True,
            "provider": "stub",
            "query": query,
            "results": [
                {
                    "title": f"Stub result for: {query}",
                    "url": "https://example.com/search",
                    "snippet": (
                        "Configure TAVILY_API_KEY or BRAVE_API_KEY for live search. "
                        "DuckDuckGo HTML scraping is intentionally not bundled."
                    ),
                }
            ][:max_results],
            "dry_run": self.dry_run or provider == "stub",
        }

    def _search_tavily(self, query: str, max_results: int) -> Dict[str, Any]:
        key = _env("TAVILY_API_KEY")
        payload = json.dumps(
            {"api_key": key, "query": query, "max_results": max_results}
        ).encode("utf-8")
        req = urllib.request.Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            for r in (data.get("results") or [])[:max_results]:
                results.append(
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "snippet": r.get("content") or r.get("snippet"),
                    }
                )
            return {"ok": True, "provider": "tavily", "query": query, "results": results}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "provider": "tavily", "error": str(e), "query": query}

    def _search_brave(self, query: str, max_results: int) -> Dict[str, Any]:
        key = _env("BRAVE_API_KEY")
        q = urllib.parse.urlencode({"q": query, "count": str(max_results)})
        req = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{q}",
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": key,
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = []
            for r in (data.get("web", {}) or {}).get("results", [])[:max_results]:
                results.append(
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "snippet": r.get("description"),
                    }
                )
            return {"ok": True, "provider": "brave", "query": query, "results": results}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "provider": "brave", "error": str(e), "query": query}

    # ── Cloud CLIs ─────────────────────────────────────────────────────

    def discover_cloud_clis(self) -> List[Dict[str, Any]]:
        names = [
            ("gcloud", "Google Cloud SDK"),
            ("aws", "AWS CLI"),
            ("az", "Azure CLI"),
            ("kubectl", "Kubernetes CLI"),
            ("terraform", "Terraform"),
            ("docker", "Docker"),
        ]
        out = []
        for cmd, desc in names:
            path = shutil.which(cmd) or shutil.which(f"{cmd}.exe")
            out.append(
                {
                    "name": cmd,
                    "description": desc,
                    "available": path is not None,
                    "path": path,
                }
            )
        return out

    def capabilities(self) -> Dict[str, Any]:
        return {
            "webhook_configured": bool(self.webhook_url()),
            "webhook_url_set": bool(self.webhook_url()),
            "tavily": bool(_env("TAVILY_API_KEY")),
            "brave": bool(_env("BRAVE_API_KEY")),
            "dry_run": self.dry_run,
            "cloud_clis": self.discover_cloud_clis(),
        }
