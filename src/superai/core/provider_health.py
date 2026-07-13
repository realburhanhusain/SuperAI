"""
Persistent provider health + quota / rate-limit tracking (Phase 2 Track F).

Stored at ~/.superai/provider_health.json
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_PATH = Path.home() / ".superai" / "provider_health.json"


class ProviderHealthStore:
    """Tracks success/failure, latency, circuit state, and simple quota windows."""

    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path or DEFAULT_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.exists():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    return raw
            except (OSError, json.JSONDecodeError):
                pass
        return {"providers": {}, "updated_at": None}

    def save(self) -> None:
        self.data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def _provider(self, name: str) -> Dict[str, Any]:
        providers = self.data.setdefault("providers", {})
        if name not in providers:
            providers[name] = {
                "successes": 0,
                "failures": 0,
                "consecutive_failures": 0,
                "total_latency": 0.0,
                "calls": 0,
                "last_error": None,
                "last_success_at": None,
                "last_failure_at": None,
                "circuit_open": False,
                "circuit_opened_at": None,
                "quota": {
                    "window_start": time.time(),
                    "window_seconds": 60,
                    "requests_in_window": 0,
                    "max_requests_per_window": 60,
                    "tokens_in_window": 0,
                    "max_tokens_per_window": 200_000,
                    "throttled": False,
                },
            }
        return providers[name]

    def record_success(
        self, provider: str, latency: float = 0.0, tokens: int = 0
    ) -> None:
        p = self._provider(provider)
        p["successes"] += 1
        p["calls"] += 1
        p["consecutive_failures"] = 0
        p["total_latency"] += float(latency)
        p["last_success_at"] = time.time()
        p["circuit_open"] = False
        p["circuit_opened_at"] = None
        self._quota_hit(provider, tokens=tokens)
        self.save()

    def record_failure(self, provider: str, error: str = "", latency: float = 0.0) -> None:
        p = self._provider(provider)
        p["failures"] += 1
        p["calls"] += 1
        p["consecutive_failures"] = int(p.get("consecutive_failures") or 0) + 1
        p["total_latency"] += float(latency)
        p["last_error"] = error[:500]
        p["last_failure_at"] = time.time()
        if p["consecutive_failures"] >= 3:
            p["circuit_open"] = True
            p["circuit_opened_at"] = time.time()
        self._quota_hit(provider, tokens=0)
        self.save()

    def _quota_hit(self, provider: str, tokens: int = 0) -> None:
        p = self._provider(provider)
        q = p.setdefault(
            "quota",
            {
                "window_start": time.time(),
                "window_seconds": 60,
                "requests_in_window": 0,
                "max_requests_per_window": 60,
                "tokens_in_window": 0,
                "max_tokens_per_window": 200_000,
                "throttled": False,
            },
        )
        now = time.time()
        window = float(q.get("window_seconds") or 60)
        if now - float(q.get("window_start") or now) > window:
            q["window_start"] = now
            q["requests_in_window"] = 0
            q["tokens_in_window"] = 0
            q["throttled"] = False
        q["requests_in_window"] = int(q.get("requests_in_window") or 0) + 1
        q["tokens_in_window"] = int(q.get("tokens_in_window") or 0) + int(tokens)
        max_req = int(q.get("max_requests_per_window") or 60)
        max_tok = int(q.get("max_tokens_per_window") or 200_000)
        q["throttled"] = (
            q["requests_in_window"] >= max_req or q["tokens_in_window"] >= max_tok
        )

    def set_quota_limits(
        self,
        provider: str,
        max_requests_per_window: Optional[int] = None,
        max_tokens_per_window: Optional[int] = None,
        window_seconds: Optional[int] = None,
    ) -> None:
        p = self._provider(provider)
        q = p.setdefault("quota", {})
        if max_requests_per_window is not None:
            q["max_requests_per_window"] = max_requests_per_window
        if max_tokens_per_window is not None:
            q["max_tokens_per_window"] = max_tokens_per_window
        if window_seconds is not None:
            q["window_seconds"] = window_seconds
        self.save()

    def health_score(self, provider: str) -> float:
        """0.0–1.0 health for router scoring."""
        p = self._provider(provider)
        if p.get("circuit_open"):
            opened = float(p.get("circuit_opened_at") or 0)
            # Half-open after 60s
            if time.time() - opened > 60:
                return 0.35
            return 0.05
        q = p.get("quota") or {}
        if q.get("throttled"):
            return 0.25
        calls = int(p.get("calls") or 0)
        if calls == 0:
            return 0.85  # unknown, slightly optimistic
        successes = int(p.get("successes") or 0)
        rate = successes / calls
        # Penalize recent consecutive failures lightly even if overall rate ok
        consec = int(p.get("consecutive_failures") or 0)
        score = rate * (1.0 - 0.1 * min(consec, 5))
        return max(0.05, min(1.0, score))

    def can_call(self, provider: str) -> bool:
        p = self._provider(provider)
        if p.get("circuit_open"):
            opened = float(p.get("circuit_opened_at") or 0)
            if time.time() - opened <= 60:
                return False
        q = p.get("quota") or {}
        if q.get("throttled"):
            # Reset window if expired
            now = time.time()
            window = float(q.get("window_seconds") or 60)
            if now - float(q.get("window_start") or now) > window:
                q["throttled"] = False
                q["window_start"] = now
                q["requests_in_window"] = 0
                q["tokens_in_window"] = 0
                self.save()
                return True
            return False
        return True

    def avg_latency(self, provider: str) -> Optional[float]:
        p = self._provider(provider)
        calls = int(p.get("calls") or 0)
        if calls <= 0:
            return None
        return float(p.get("total_latency") or 0) / calls

    def snapshot(self) -> Dict[str, Any]:
        out = {}
        for name, p in (self.data.get("providers") or {}).items():
            calls = int(p.get("calls") or 0)
            successes = int(p.get("successes") or 0)
            out[name] = {
                "health": round(self.health_score(name), 3),
                "success_rate": round(successes / calls, 3) if calls else None,
                "calls": calls,
                "failures": p.get("failures"),
                "circuit_open": p.get("circuit_open"),
                "avg_latency": self.avg_latency(name),
                "quota": p.get("quota"),
                "can_call": self.can_call(name),
                "last_error": p.get("last_error"),
            }
        return out

    def apply_to_circuit_breakers(self, load_balancer) -> None:
        """Hydrate LoadBalancer circuit breakers from persisted state."""
        for name, p in (self.data.get("providers") or {}).items():
            cb = load_balancer.get_circuit_breaker(name)
            cb.failures = int(p.get("consecutive_failures") or 0)
            cb.is_open = bool(p.get("circuit_open"))
            cb.last_failure_time = float(p.get("last_failure_at") or 0)
