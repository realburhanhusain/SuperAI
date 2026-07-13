"""
Multi-model council with selectable voting (inspired by LLM_Council).

Voting modes (user-selectable):
  - majority: most frequent stance label / vote_key
  - supervisor: designated supervisor model picks winner
  - weighted: score by model cost/latency/health weights

Stages: propose → (optional critique) → vote → aggregate
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from .model_caller import ModelCaller
from .model_registry import ModelRegistry
from .provider_health import ProviderHealthStore

VOTING_MODES = ("majority", "supervisor", "weighted")


def parse_vote_mode(value: Optional[str]) -> str:
    v = (value or "majority").strip().lower()
    if v not in VOTING_MODES:
        return "majority"
    return v


class Council:
    def __init__(
        self,
        caller: Optional[ModelCaller] = None,
        registry: Optional[ModelRegistry] = None,
        health: Optional[ProviderHealthStore] = None,
        voting_mode: str = "majority",
        supervisor_model: Optional[str] = None,
    ):
        self.registry = registry or ModelRegistry()
        self.caller = caller or ModelCaller(use_mock=True, registry=self.registry)
        self.health = health or ProviderHealthStore()
        self.voting_mode = parse_vote_mode(voting_mode)
        self.supervisor_model = supervisor_model

    def run(
        self,
        topic: str,
        models: Optional[List[str]] = None,
        voting_mode: Optional[str] = None,
        supervisor_model: Optional[str] = None,
        with_critique: bool = False,
    ) -> Dict[str, Any]:
        mode = parse_vote_mode(voting_mode or self.voting_mode)
        supervisor = supervisor_model or self.supervisor_model
        members = models or self._default_models(3)

        # Stage 1: structured proposals
        proposals: List[Dict[str, Any]] = []
        for m in members:
            prompt = (
                "You are a council member. Respond with ONLY valid JSON:\n"
                '{"stance":"short label","vote_key":"snake_case_key",'
                '"confidence":0.0-1.0,"reasons":["..."],"summary":"..."}\n\n'
                f"Topic: {topic}"
            )
            raw = self.caller.call(model=m, prompt=prompt)
            parsed = self._parse_member_json(str(raw.get("response") or ""), m)
            parsed["model"] = m
            parsed["raw_mock"] = bool(raw.get("mock"))
            proposals.append(parsed)

        # Stage 2: optional critique pass
        critiques: List[Dict[str, Any]] = []
        if with_critique and len(proposals) >= 2:
            for i, p in enumerate(proposals):
                other = proposals[(i + 1) % len(proposals)]
                prompt = (
                    f"Topic: {topic}\nPeer stance: {other.get('summary')}\n"
                    f"Your prior stance: {p.get('summary')}\n"
                    "Reply JSON: "
                    '{"vote_key":"...","confidence":0-1,"summary":"refined"}'
                )
                raw = self.caller.call(model=p["model"], prompt=prompt)
                refined = self._parse_member_json(str(raw.get("response") or ""), p["model"])
                p["vote_key"] = refined.get("vote_key") or p.get("vote_key")
                p["confidence"] = refined.get("confidence", p.get("confidence"))
                p["summary"] = refined.get("summary") or p.get("summary")
                critiques.append({"model": p["model"], "refined": refined})

        # Stage 3: vote / aggregate
        decision = self._aggregate(
            topic=topic,
            proposals=proposals,
            mode=mode,
            supervisor=supervisor,
            members=members,
        )

        return {
            "topic": topic,
            "voting_mode": mode,
            "members": members,
            "proposals": proposals,
            "critiques": critiques,
            "decision": decision,
            "message": f"Council finished via {mode} voting.",
        }

    def _aggregate(
        self,
        topic: str,
        proposals: List[Dict[str, Any]],
        mode: str,
        supervisor: Optional[str],
        members: List[str],
    ) -> Dict[str, Any]:
        if mode == "majority":
            keys = [p.get("vote_key") or "undecided" for p in proposals]
            counts = Counter(keys)
            winner_key, votes = counts.most_common(1)[0]
            winners = [p for p in proposals if p.get("vote_key") == winner_key]
            return {
                "mode": "majority",
                "winner_vote_key": winner_key,
                "votes": votes,
                "tally": dict(counts),
                "winner_models": [p["model"] for p in winners],
                "summary": winners[0].get("summary") if winners else "",
            }

        if mode == "weighted":
            scores: Dict[str, float] = {}
            weight_detail: Dict[str, float] = {}
            for p in proposals:
                key = p.get("vote_key") or "undecided"
                conf = float(p.get("confidence") or 0.5)
                model = p["model"]
                info = self.registry.get_model(model)
                cost = float(info.cost_per_1k_tokens) if info else 0.005
                cost_w = 1.0 / (1.0 + cost * 50)
                health = self.health.health_score(info.provider if info else "unknown")
                w = conf * 0.5 + cost_w * 0.25 + health * 0.25
                scores[key] = scores.get(key, 0.0) + w
                weight_detail[model] = round(w, 4)
            winner_key = max(scores, key=scores.get) if scores else "undecided"
            winners = [p for p in proposals if p.get("vote_key") == winner_key]
            return {
                "mode": "weighted",
                "winner_vote_key": winner_key,
                "scores": {k: round(v, 4) for k, v in scores.items()},
                "member_weights": weight_detail,
                "winner_models": [p["model"] for p in winners],
                "summary": winners[0].get("summary") if winners else "",
            }

        # supervisor picks
        sup = supervisor or members[0]
        ballot = json.dumps(
            [
                {
                    "model": p["model"],
                    "vote_key": p.get("vote_key"),
                    "summary": p.get("summary"),
                    "confidence": p.get("confidence"),
                }
                for p in proposals
            ],
            indent=2,
        )
        prompt = (
            f"You are the council supervisor. Topic: {topic}\n"
            f"Ballots:\n{ballot}\n"
            "Pick the best proposal. Reply ONLY JSON: "
            '{"winner_model":"...","winner_vote_key":"...","rationale":"..."}'
        )
        raw = self.caller.call(model=sup, prompt=prompt)
        parsed = self._parse_json_loose(str(raw.get("response") or ""))
        winner_model = parsed.get("winner_model") or members[0]
        winner_key = parsed.get("winner_vote_key")
        match = next((p for p in proposals if p["model"] == winner_model), proposals[0])
        if not winner_key:
            winner_key = match.get("vote_key")
        return {
            "mode": "supervisor",
            "supervisor_model": sup,
            "winner_model": winner_model,
            "winner_vote_key": winner_key,
            "rationale": parsed.get("rationale") or "",
            "summary": match.get("summary"),
        }

    def _default_models(self, n: int) -> List[str]:
        names = self.registry.list_all_models()
        if not names:
            return ["gpt-4o"] * n
        return names[:n]

    def _parse_member_json(self, text: str, model: str) -> Dict[str, Any]:
        data = self._parse_json_loose(text)
        vote_key = data.get("vote_key") or data.get("stance") or "undecided"
        vote_key = re.sub(r"[^a-z0-9_]+", "_", str(vote_key).lower()).strip("_") or "undecided"
        conf = data.get("confidence", 0.6)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.6
        conf = max(0.0, min(1.0, conf))
        summary = data.get("summary") or data.get("stance") or text[:300]
        reasons = data.get("reasons") if isinstance(data.get("reasons"), list) else []
        # Mock-friendly fallback when model returns prose
        if "mock response" in text.lower() or not data:
            vote_key = f"stance_{model.replace('-', '_')[:20]}"
            summary = text[:300]
            conf = 0.55
        return {
            "stance": data.get("stance") or vote_key,
            "vote_key": vote_key,
            "confidence": conf,
            "reasons": reasons,
            "summary": summary,
        }

    def _parse_json_loose(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {}
        try:
            obj = json.loads(text)
            return obj if isinstance(obj, dict) else {}
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                obj = json.loads(m.group(0))
                return obj if isinstance(obj, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}
