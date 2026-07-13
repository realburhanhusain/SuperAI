"""
Model Router for SuperAI — scoring-based selection (Phase 2).

score = (
    0.35 * task_type_match +
    0.25 * historical_success_rate +
    0.20 * cost_efficiency +
    0.15 * latency_score +
    0.05 * provider_health
)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .load_balancer import LoadBalancer, LoadBalancingStrategy
from .logger import get_logger
from .model_registry import ModelInfo, ModelRegistry
from .provider_health import ProviderHealthStore
from .routing_stats import compute_model_stats

logger = get_logger("superai.router")


class ModelRouter:
    def __init__(
        self,
        registry: ModelRegistry,
        load_balancer: Optional[LoadBalancer] = None,
        history_stats: Optional[Dict[str, Dict[str, Any]]] = None,
        health_store: Optional[ProviderHealthStore] = None,
    ):
        self.registry = registry
        self.load_balancer = load_balancer or LoadBalancer(
            strategy=LoadBalancingStrategy.SMART_FALLBACK
        )
        self.health_store = health_store or ProviderHealthStore()
        try:
            self.health_store.apply_to_circuit_breakers(self.load_balancer)
        except Exception:  # noqa: BLE001
            pass
        # Precomputed task-history stats; refreshed via refresh_history_stats()
        self._history_stats = history_stats or {}
        self.last_scores: List[Dict[str, Any]] = []

    def refresh_history_stats(self, limit: int = 200) -> None:
        self._history_stats = compute_model_stats(limit=limit)

    def classify_task(self, task: str) -> str:
        task_lower = (task or "").lower()
        if any(
            w in task_lower
            for w in [
                "code",
                "implement",
                "build",
                "create api",
                "function",
                "fastapi",
                "bug",
                "refactor",
                "python",
                "typescript",
                "test",
            ]
        ):
            return "coding"
        if any(
            w in task_lower
            for w in ["reason", "analyze", "compare", "explain", "prove", "debate"]
        ):
            return "reasoning"
        if any(
            w in task_lower
            for w in ["search", "latest", "news", "current", "research"]
        ):
            return "research"
        if any(w in task_lower for w in ["story", "poem", "creative", "brainstorm"]):
            return "creative"
        return "general"

    def score_model(
        self,
        model: ModelInfo,
        task_type: str,
    ) -> Tuple[float, Dict[str, float]]:
        """Return (total_score, component_breakdown)."""
        strengths = model.extra.get("task_strengths") if model.extra else None
        if not isinstance(strengths, dict):
            strengths = {}
        # Prefer structured strengths; fall back to heuristic from free-text
        task_match = float(strengths.get(task_type, strengths.get("general", 0.6)))
        if task_match == 0.6 and model.strengths:
            # light keyword boost from free-text strengths
            s = model.strengths.lower()
            if task_type == "coding" and "cod" in s:
                task_match = 0.85
            elif task_type == "reasoning" and "reason" in s:
                task_match = 0.85

        import math

        hist = self._history_stats.get(model.name) or {}
        if hist.get("total", 0) >= 1:
            hist_success = float(hist.get("success_rate", 0.7))
        else:
            hist_success = 0.7  # neutral prior

        # Compress cost so ultra-cheap models don't dominate capability match
        cost = model.cost_per_1k_tokens if model.cost_per_1k_tokens > 0 else 0.005
        cost_efficiency = max(0.0, min(1.0, 1.0 - (math.log10(1.0 + cost * 1000.0) / 3.0)))

        # latency_tier 1..5 → score 1.0 .. 0.2 (gentle)
        latency_tier = max(1, min(5, model.latency_tier or 2))
        latency_score = (6 - latency_tier) / 5.0

        # Prefer persisted health store; fall back to in-process circuit breaker
        try:
            provider_health = float(self.health_store.health_score(model.provider))
        except Exception:  # noqa: BLE001
            provider_health = self.load_balancer.provider_health(model.provider)

        # Plan weights (implementation_plan_v2 §2.3)
        total = (
            0.35 * task_match
            + 0.25 * hist_success
            + 0.20 * cost_efficiency
            + 0.15 * latency_score
            + 0.05 * provider_health
        )
        parts = {
            "task_type_match": round(task_match, 3),
            "historical_success_rate": round(hist_success, 3),
            "cost_efficiency": round(cost_efficiency, 3),
            "latency_score": round(latency_score, 3),
            "provider_health": round(provider_health, 3),
            "total": round(total, 4),
        }
        return total, parts

    def rank_models(self, task: str) -> List[Tuple[ModelInfo, Dict[str, float]]]:
        task_type = self.classify_task(task)
        ranked: List[Tuple[ModelInfo, Dict[str, float]]] = []
        for name in self.registry.list_all_models():
            model = self.registry.get_model(name)
            if not model:
                continue
            _, parts = self.score_model(model, task_type)
            ranked.append((model, parts))
        ranked.sort(key=lambda x: x[1]["total"], reverse=True)
        self.last_scores = [
            {"model": m.name, "provider": m.provider, **parts} for m, parts in ranked[:15]
        ]
        return ranked

    def get_best_model(
        self,
        task: str,
        preferred_model: Optional[str] = None,
    ) -> Optional[ModelInfo]:
        if preferred_model:
            model = self.registry.get_model(preferred_model)
            if model:
                return model

        if not self._history_stats:
            try:
                self.refresh_history_stats()
            except Exception:  # noqa: BLE001
                pass

        ranked = self.rank_models(task)
        return ranked[0][0] if ranked else None

    def select_model(
        self,
        task_description: str,
        preferred_model: Optional[str] = None,
        context: str = "",
        verbose: bool = False,
    ) -> str:
        _ = context
        model = self.get_best_model(task_description, preferred_model=preferred_model)
        if model:
            if verbose:
                task_type = self.classify_task(task_description)
                _, parts = self.score_model(model, task_type)
                logger.info(
                    "Selected %s (provider=%s, type=%s, score=%s)",
                    model.name,
                    model.provider,
                    task_type,
                    parts.get("total"),
                )
            return model.name
        return preferred_model or "mock-model"

    def explain_selection(self, task: str, top_k: int = 5) -> List[Dict[str, Any]]:
        ranked = self.rank_models(task)
        out = []
        for model, parts in ranked[:top_k]:
            out.append(
                {
                    "model": model.name,
                    "provider": model.provider,
                    "score": parts["total"],
                    "components": parts,
                }
            )
        return out

    def get_providers_for_model(self, model_name: str) -> List[str]:
        model = self.registry.get_model(model_name)
        if not model:
            return []
        # Primary provider + same-base_url peers as soft fallbacks
        providers = [model.provider]
        for other_name in self.registry.list_all_models():
            other = self.registry.get_model(other_name)
            if not other or other.name == model.name:
                continue
            if other.model_id == model.model_id and other.provider not in providers:
                providers.append(other.provider)
        return providers
