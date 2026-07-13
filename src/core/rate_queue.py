"""
Rate-limit aware retry queue (M13).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .error_recovery import classify_error


class RateLimitQueue:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or (Path.home() / ".superai" / "rate_queue.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {"items": [], "backoff_sec": 30}

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def enqueue(self, kind: str, payload: Dict[str, Any], error: str = "") -> Dict[str, Any]:
        item = {
            "id": f"q-{int(time.time()*1000)}",
            "kind": kind,
            "payload": payload,
            "error": error,
            "enqueued_at": time.time(),
            "not_before": time.time() + float(self.data.get("backoff_sec") or 30),
            "attempts": 0,
        }
        self.data.setdefault("items", []).append(item)
        self.save()
        return item

    def due(self) -> List[Dict[str, Any]]:
        now = time.time()
        return [i for i in self.data.get("items") or [] if float(i.get("not_before") or 0) <= now]

    def list_items(self) -> List[Dict[str, Any]]:
        return list(self.data.get("items") or [])

    def remove(self, item_id: str) -> bool:
        before = len(self.data.get("items") or [])
        self.data["items"] = [i for i in (self.data.get("items") or []) if i.get("id") != item_id]
        self.save()
        return len(self.data["items"]) < before

    def run_with_retry(
        self,
        fn: Callable[[], Any],
        *,
        kind: str = "call",
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        base_backoff: float = 2.0,
    ) -> Any:
        """Call fn; on rate_limit/network, backoff and retry."""
        last_err: Optional[BaseException] = None
        for attempt in range(max_retries + 1):
            try:
                return fn()
            except Exception as e:  # noqa: BLE001
                last_err = e
                info = classify_error(e)
                if not info.get("retryable") or attempt >= max_retries:
                    self.enqueue(kind, payload or {}, error=str(e))
                    raise
                sleep_s = base_backoff * (2**attempt)
                time.sleep(min(sleep_s, 60))
        if last_err:
            raise last_err
        raise RuntimeError("retry failed")
