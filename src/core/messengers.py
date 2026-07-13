"""
Multi-messenger bus (Atomic-Hermes inspired).

Unified outbound interface with channel adapters:
  cli, file, webhook, telegram, slack.

Env / config:
  SUPERAI_WEBHOOK_URL
  SUPERAI_TELEGRAM_BOT_TOKEN + SUPERAI_TELEGRAM_CHAT_ID
  SUPERAI_SLACK_WEBHOOK_URL  (or SUPERAI_SLACK_BOT_TOKEN + SUPERAI_SLACK_CHANNEL)
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "on"}


class MessengerBus:
    """
    Outbound/inbound message log with channel adapters.

    Always-on: cli, file.
    Configured when env present: webhook, telegram, slack.
    Dry-run mode logs payload without network (SUPERAI_MESSENGER_DRY_RUN=1).
    """

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "messenger_log.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.dry_run = _env_truthy("SUPERAI_MESSENGER_DRY_RUN")
        self.channels = self._build_channel_map()

    def _build_channel_map(self) -> Dict[str, Dict[str, Any]]:
        tg_token = (os.getenv("SUPERAI_TELEGRAM_BOT_TOKEN") or "").strip()
        tg_chat = (os.getenv("SUPERAI_TELEGRAM_CHAT_ID") or "").strip()
        slack_hook = (os.getenv("SUPERAI_SLACK_WEBHOOK_URL") or "").strip()
        slack_token = (os.getenv("SUPERAI_SLACK_BOT_TOKEN") or "").strip()
        slack_channel = (os.getenv("SUPERAI_SLACK_CHANNEL") or "").strip()
        webhook = (os.getenv("SUPERAI_WEBHOOK_URL") or "").strip()

        return {
            "cli": {
                "enabled": True,
                "description": "Terminal / SuperAI CLI",
                "configured": True,
            },
            "file": {
                "enabled": True,
                "description": "Append to ~/.superai/messenger_outbox.txt",
                "configured": True,
            },
            "webhook": {
                "enabled": bool(webhook) or self.dry_run,
                "description": "HTTP webhook (SUPERAI_WEBHOOK_URL)",
                "configured": bool(webhook),
            },
            "telegram": {
                "enabled": bool(tg_token and tg_chat) or self.dry_run,
                "description": "Telegram Bot API (SUPERAI_TELEGRAM_BOT_TOKEN + CHAT_ID)",
                "configured": bool(tg_token and tg_chat),
            },
            "slack": {
                "enabled": bool(slack_hook or (slack_token and slack_channel))
                or self.dry_run,
                "description": "Slack incoming webhook or chat.postMessage",
                "configured": bool(slack_hook or (slack_token and slack_channel)),
            },
        }

    def list_channels(self) -> Dict[str, Any]:
        # Refresh enablement from env each call
        self.channels = self._build_channel_map()
        return {
            **self.channels,
            "_meta": {
                "dry_run": self.dry_run,
                "log": str(self.path),
            },
        }

    def send(
        self,
        message: str,
        channel: str = "cli",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.channels = self._build_channel_map()
        ch = channel.lower().strip()
        if ch not in self.channels:
            return {"ok": False, "error": f"Unknown channel: {channel}"}
        if not self.channels[ch].get("enabled") and ch not in {"cli", "file"}:
            return {
                "ok": False,
                "error": f"Channel {ch} not enabled/configured",
                "channel": ch,
                "hint": self.channels[ch].get("description"),
            }

        entry: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "channel": ch,
            "message": message,
            "metadata": metadata or {},
            "direction": "out",
            "dry_run": self.dry_run,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        if ch == "cli":
            return {"ok": True, "channel": ch, "logged": True, "entry": entry}

        if ch == "file":
            outbox = self.path.parent / "messenger_outbox.txt"
            with open(outbox, "a", encoding="utf-8") as f:
                f.write(f"[{entry['ts']}] {message}\n")
            return {"ok": True, "channel": ch, "logged": True, "entry": entry}

        if ch == "webhook":
            return self._send_webhook(message, metadata, entry)

        if ch == "telegram":
            return self._send_telegram(message, metadata, entry)

        if ch == "slack":
            return self._send_slack(message, metadata, entry)

        return {"ok": False, "error": f"No handler for {ch}"}

    def _http_json(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "ok": True,
                "dry_run": True,
                "url": url,
                "payload": payload,
            }
        body = json.dumps(payload).encode("utf-8")
        hdrs = {"Content-Type": "application/json", **(headers or {})}
        req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    data = {"raw": raw[:500]}
                return {"ok": True, "status": resp.status, "response": data}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
            return {"ok": False, "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "error": str(e)}

    def _send_webhook(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]],
        entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        url = (os.getenv("SUPERAI_WEBHOOK_URL") or "").strip()
        if not url and not self.dry_run:
            return {"ok": False, "error": "SUPERAI_WEBHOOK_URL not set", "logged": True}
        payload = {"text": message, **(metadata or {})}
        result = self._http_json(url or "https://example.invalid/webhook", payload)
        entry["transport"] = result
        return {
            "ok": bool(result.get("ok")),
            "channel": "webhook",
            "logged": True,
            "entry": entry,
            **{k: v for k, v in result.items() if k != "ok"},
            "error": result.get("error"),
        }

    def _send_telegram(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]],
        entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        token = (os.getenv("SUPERAI_TELEGRAM_BOT_TOKEN") or "").strip()
        chat_id = (os.getenv("SUPERAI_TELEGRAM_CHAT_ID") or "").strip()
        if (not token or not chat_id) and not self.dry_run:
            return {
                "ok": False,
                "error": "Set SUPERAI_TELEGRAM_BOT_TOKEN and SUPERAI_TELEGRAM_CHAT_ID",
                "logged": True,
            }
        # Prefer chat_id from metadata when present
        chat = str((metadata or {}).get("chat_id") or chat_id or "0")
        url = f"https://api.telegram.org/bot{token or 'DRY_RUN'}/sendMessage"
        payload = {
            "chat_id": chat,
            "text": message,
            "disable_web_page_preview": True,
        }
        parse_mode = (metadata or {}).get("parse_mode")
        if parse_mode:
            payload["parse_mode"] = parse_mode
        result = self._http_json(url, payload)
        entry["transport"] = result
        # Telegram returns ok:true in body
        if result.get("ok") and isinstance(result.get("response"), dict):
            if result["response"].get("ok") is False:
                return {
                    "ok": False,
                    "channel": "telegram",
                    "logged": True,
                    "error": result["response"].get("description"),
                    "entry": entry,
                }
        return {
            "ok": bool(result.get("ok")),
            "channel": "telegram",
            "logged": True,
            "entry": entry,
            "error": result.get("error"),
            "dry_run": result.get("dry_run"),
        }

    def _send_slack(
        self,
        message: str,
        metadata: Optional[Dict[str, Any]],
        entry: Dict[str, Any],
    ) -> Dict[str, Any]:
        hook = (os.getenv("SUPERAI_SLACK_WEBHOOK_URL") or "").strip()
        token = (os.getenv("SUPERAI_SLACK_BOT_TOKEN") or "").strip()
        channel = (
            str((metadata or {}).get("channel") or os.getenv("SUPERAI_SLACK_CHANNEL") or "")
            .strip()
        )

        if hook or self.dry_run and not token:
            # Incoming webhook
            url = hook or "https://hooks.slack.com/services/DRY/RUN/TOKEN"
            payload = {"text": message}
            if (metadata or {}).get("blocks"):
                payload["blocks"] = metadata["blocks"]  # type: ignore[index]
            result = self._http_json(url, payload)
        elif token and channel:
            url = "https://slack.com/api/chat.postMessage"
            payload = {"channel": channel, "text": message}
            result = self._http_json(
                url,
                payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            # Slack API wraps success in body.ok
            if result.get("ok") and isinstance(result.get("response"), dict):
                if result["response"].get("ok") is False:
                    return {
                        "ok": False,
                        "channel": "slack",
                        "logged": True,
                        "error": result["response"].get("error"),
                        "entry": entry,
                    }
        else:
            return {
                "ok": False,
                "error": "Set SUPERAI_SLACK_WEBHOOK_URL or BOT_TOKEN+CHANNEL",
                "logged": True,
            }

        entry["transport"] = result
        return {
            "ok": bool(result.get("ok")),
            "channel": "slack",
            "logged": True,
            "entry": entry,
            "error": result.get("error"),
            "dry_run": result.get("dry_run"),
        }

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

    def broadcast(
        self,
        message: str,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send to multiple enabled channels."""
        self.channels = self._build_channel_map()
        targets = channels or [
            name
            for name, info in self.channels.items()
            if info.get("enabled") and name != "cli"
        ]
        results = {}
        for ch in targets:
            results[ch] = self.send(message, channel=ch, metadata=metadata)
        ok_any = any(r.get("ok") for r in results.values())
        return {"ok": ok_any, "results": results}
