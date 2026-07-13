"""
Multi-messenger stubs (Atomic-Hermes inspired).

Provides a unified interface; real transports can be plugged in later.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class MessengerBus:
    """
    Outbound/inbound message log with channel adapters.

    Channels: cli (always), file, webhook (log-only until configured).
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "messenger_log.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.channels = {
            "cli": {"enabled": True, "description": "Terminal / SuperAI CLI"},
            "file": {
                "enabled": True,
                "description": "Append to ~/.superai/messenger_outbox.txt",
            },
            "webhook": {
                "enabled": False,
                "description": "HTTP webhook (set SUPERAI_WEBHOOK_URL)",
            },
            "telegram": {
                "enabled": False,
                "description": "Telegram bot (configure token later)",
            },
            "slack": {
                "enabled": False,
                "description": "Slack webhook (configure later)",
            },
        }

    def list_channels(self) -> Dict[str, Any]:
        return self.channels

    def send(
        self,
        message: str,
        channel: str = "cli",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ch = channel.lower()
        if ch not in self.channels:
            return {"ok": False, "error": f"Unknown channel: {channel}"}
        if not self.channels[ch].get("enabled") and ch not in {"cli", "file"}:
            return {
                "ok": False,
                "error": f"Channel {ch} not enabled/configured",
                "channel": ch,
            }

        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "channel": ch,
            "message": message,
            "metadata": metadata or {},
            "direction": "out",
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if ch == "file":
            outbox = self.path.parent / "messenger_outbox.txt"
            with open(outbox, "a", encoding="utf-8") as f:
                f.write(f"[{entry['ts']}] {message}\n")

        if ch == "webhook":
            import os
            import urllib.request

            url = os.getenv("SUPERAI_WEBHOOK_URL")
            if not url:
                return {"ok": False, "error": "SUPERAI_WEBHOOK_URL not set"}
            req = urllib.request.Request(
                url,
                data=json.dumps({"text": message, **(metadata or {})}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    entry["status"] = resp.status
            except Exception as e:  # noqa: BLE001
                return {"ok": False, "error": str(e), "logged": True}

        return {"ok": True, "channel": ch, "logged": True, "entry": entry}

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        out = []
        for line in lines[-limit:]:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(reversed(out))
