"""
Multi-turn chat session (S2).
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from .constitution import format_for_prompt
from .secrets import redact_text


class ChatSession:
    def __init__(self, path: Optional[Path] = None):
        self.root = Path(path or (Path.home() / ".superai" / "chats"))
        self.root.mkdir(parents=True, exist_ok=True)

    def _file(self, sid: str) -> Path:
        return self.root / f"{sid}.json"

    def start(self, system_extra: str = "") -> str:
        sid = f"chat-{uuid.uuid4().hex[:10]}"
        data = {
            "id": sid,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "messages": [
                {
                    "role": "system",
                    "content": format_for_prompt() + (system_extra or ""),
                }
            ],
        }
        self._save(sid, data)
        return sid

    def _load(self, sid: str) -> Dict[str, Any]:
        p = self._file(sid)
        if not p.exists():
            raise KeyError(f"Unknown chat: {sid}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, sid: str, data: Dict[str, Any]) -> None:
        self._file(sid).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def ask(
        self,
        sid: str,
        user_message: str,
        model: Optional[str] = None,
        use_mock: Optional[bool] = None,
    ) -> Dict[str, Any]:
        from .config import Config
        from .model_caller import ModelCaller
        from .model_registry import ModelRegistry
        from .model_router import ModelRouter

        data = self._load(sid)
        data["messages"].append({"role": "user", "content": redact_text(user_message)})

        cfg = Config()
        mock = cfg.use_mock if use_mock is None else use_mock
        reg = ModelRegistry()
        router = ModelRouter(reg)
        chosen = model or router.select_model(user_message) or "gpt-4o"
        caller = ModelCaller(use_mock=mock, registry=reg)

        # Build transcript prompt
        lines = []
        for m in data["messages"][-12:]:
            lines.append(f"{m['role'].upper()}: {m['content']}")
        prompt = "\n".join(lines) + "\nASSISTANT:"
        result = caller.call(model=chosen, prompt=prompt)
        reply = redact_text(str(result.get("response") or ""))
        data["messages"].append({"role": "assistant", "content": reply, "model": chosen})
        self._save(sid, data)
        return {
            "chat_id": sid,
            "model": chosen,
            "reply": reply,
            "mock": result.get("mock"),
            "turns": len([m for m in data["messages"] if m["role"] == "user"]),
        }

    def history(self, sid: str) -> Dict[str, Any]:
        return self._load(sid)

    def list_chats(self) -> List[Dict[str, Any]]:
        out = []
        for p in sorted(self.root.glob("chat-*.json"), reverse=True)[:30]:
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": d.get("id"),
                        "created_at": d.get("created_at"),
                        "messages": len(d.get("messages") or []),
                    }
                )
            except Exception:
                continue
        return out
