"""
Load Balancer for SuperAI

Strategies, Circuit Breaker, retry with exponential backoff + jitter.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class LoadBalancingStrategy(str, Enum):
    SMART_FALLBACK = "smart_fallback"
    ROUND_ROBIN = "round_robin"
    LATENCY_BASED = "latency_based"
    COST_BASED = "cost_based"


def parse_strategy(value: Optional[str]) -> LoadBalancingStrategy:
    if not value:
        return LoadBalancingStrategy.SMART_FALLBACK
    normalized = str(value).strip().lower().replace("-", "_")
    for s in LoadBalancingStrategy:
        if s.value == normalized or s.name.lower() == normalized:
            return s
    return LoadBalancingStrategy.SMART_FALLBACK


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    reset_timeout: int = 60
    failures: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.is_open = True

    def record_success(self) -> None:
        self.failures = 0
        self.is_open = False

    def can_try(self) -> bool:
        if not self.is_open:
            return True
        if time.time() - self.last_failure_time > self.reset_timeout:
            self.is_open = False
            self.failures = 0
            return True
        return False


@dataclass
class ProviderCandidate:
    provider: str
    model_name: str
    cost_per_1k: float = 0.0
    latency_tier: int = 2


class LoadBalancer:
    def __init__(
        self,
        strategy: LoadBalancingStrategy | str = LoadBalancingStrategy.SMART_FALLBACK,
    ):
        self.strategy = (
            strategy
            if isinstance(strategy, LoadBalancingStrategy)
            else parse_strategy(str(strategy))
        )
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.latency_history: Dict[str, List[float]] = {}
        self.round_robin_index = 0
        self.call_log: List[Dict[str, Any]] = []

    def set_strategy(self, strategy: LoadBalancingStrategy | str) -> None:
        self.strategy = (
            strategy
            if isinstance(strategy, LoadBalancingStrategy)
            else parse_strategy(str(strategy))
        )

    def get_circuit_breaker(self, provider: str) -> CircuitBreaker:
        if provider not in self.circuit_breakers:
            self.circuit_breakers[provider] = CircuitBreaker()
        return self.circuit_breakers[provider]

    def provider_health(self, provider: str) -> float:
        cb = self.get_circuit_breaker(provider)
        if cb.is_open and not cb.can_try():
            return 0.0
        return max(0.2, 1.0 - 0.2 * cb.failures)

    def order_providers(
        self,
        candidates: List[ProviderCandidate],
    ) -> List[ProviderCandidate]:
        """Order provider candidates according to strategy."""
        if not candidates:
            return []

        usable = [c for c in candidates if self.get_circuit_breaker(c.provider).can_try()]
        if not usable:
            # All open — try them anyway in original order (half-open attempt)
            usable = list(candidates)

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            if not usable:
                return []
            idx = self.round_robin_index % len(usable)
            self.round_robin_index += 1
            return usable[idx:] + usable[:idx]

        if self.strategy == LoadBalancingStrategy.LATENCY_BASED:

            def latency_key(c: ProviderCandidate) -> float:
                hist = self.latency_history.get(c.provider) or []
                avg = sum(hist) / len(hist) if hist else float(c.latency_tier)
                return avg

            return sorted(usable, key=latency_key)

        if self.strategy == LoadBalancingStrategy.COST_BASED:
            return sorted(usable, key=lambda c: c.cost_per_1k if c.cost_per_1k > 0 else 999.0)

        # SMART_FALLBACK: primary first, then by health * inverse cost
        def smart_key(c: ProviderCandidate) -> float:
            health = self.provider_health(c.provider)
            cost_factor = 1.0 / (c.cost_per_1k + 0.001)
            return -(health * 0.7 + min(cost_factor, 10) * 0.03)

        return sorted(usable, key=smart_key)

    def execute_with_fallback(
        self,
        providers: List[str] | List[ProviderCandidate],
        model_name: str,
        call_fn: Callable[[str], Any],
        max_retries_per_provider: int = 1,
    ) -> Any:
        """
        Execute call_fn(provider) with circuit breaker, backoff, and fallback.

        call_fn receives the provider string and should raise on hard failure.
        Soft failures (dict with status=error) are treated as failures when
        `raise_on_error_status` is encoded by call_fn raising.
        """
        candidates: List[ProviderCandidate] = []
        for p in providers:
            if isinstance(p, ProviderCandidate):
                candidates.append(p)
            else:
                candidates.append(ProviderCandidate(provider=str(p), model_name=model_name))

        ordered = self.order_providers(candidates)
        last_exception: Optional[BaseException] = None
        last_result: Any = None

        for cand in ordered:
            provider = cand.provider
            cb = self.get_circuit_breaker(provider)
            if not cb.can_try():
                continue

            for attempt in range(max_retries_per_provider + 1):
                try:
                    start = time.time()
                    result = call_fn(provider)
                    duration = time.time() - start

                    hist = self.latency_history.setdefault(provider, [])
                    hist.append(duration)
                    if len(hist) > 50:
                        del hist[:-50]

                    # Treat explicit error payloads as failure when present
                    if isinstance(result, dict) and result.get("status") == "error":
                        raise RuntimeError(result.get("response") or "provider error")

                    cb.record_success()
                    self.call_log.append(
                        {
                            "provider": provider,
                            "model": model_name,
                            "duration": duration,
                            "success": True,
                        }
                    )
                    if isinstance(result, dict):
                        result = {
                            **result,
                            "latency_seconds": round(duration, 4),
                            "provider_attempted": provider,
                        }
                    return result

                except Exception as e:  # noqa: BLE001
                    cb.record_failure()
                    last_exception = e
                    self.call_log.append(
                        {
                            "provider": provider,
                            "model": model_name,
                            "success": False,
                            "error": str(e),
                        }
                    )
                    # Exponential backoff + jitter
                    sleep_s = min(2**cb.failures, 8) + random.uniform(0, 0.25)
                    time.sleep(sleep_s)

        if last_exception:
            raise last_exception
        raise RuntimeError("All providers failed or are in circuit breaker state.")

    def stats_snapshot(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "circuit_breakers": {
                p: {
                    "failures": cb.failures,
                    "is_open": cb.is_open,
                    "can_try": cb.can_try(),
                }
                for p, cb in self.circuit_breakers.items()
            },
            "avg_latency": {
                p: (sum(v) / len(v) if v else None)
                for p, v in self.latency_history.items()
            },
            "recent_calls": self.call_log[-20:],
        }
