"""
Memory ontology layer (Memory Roadmap P0.4 → P6 / Cognee gap 6).

Hybrid model:
  - Core entity types + relations live in ``data/memory_ontology.yaml``
  - Free labels map to core types via aliases / known_entities
  - Unknown labels or domain/range violations → ``provisional=true``
    (not hard-rejected — offline extract stays useful)

Does not replace the knowledge graph; it normalizes labels before write.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

_DEFAULT_REL = "RELATED_TO"
_DEFAULT_TYPE = "Entity"


def default_ontology_path() -> Path:
    env = (os.getenv("SUPERAI_ONTOLOGY_PATH") or "").strip()
    if env:
        return Path(env).expanduser()
    return Path(__file__).resolve().parent / "data" / "memory_ontology.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "PyYAML required for ontology: pip install pyyaml"
        ) from e
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("ontology root must be a mapping")
    return data


def _norm_key(s: str) -> str:
    return re.sub(r"[\s_\-]+", "", (s or "").strip().lower())


class MemoryOntology:
    """Loaded controlled vocabulary with map/validate helpers."""

    def __init__(self, data: Dict[str, Any], *, path: Optional[Path] = None):
        self.data = data
        self.path = path
        self.version = str(data.get("version") or "0")
        self.name = str(data.get("name") or "ontology")
        self.map_threshold = float(data.get("map_confidence_threshold") or 0.7)
        self.entity_types: Dict[str, Dict[str, Any]] = dict(
            data.get("entity_types") or {}
        )
        self.relations: Dict[str, Dict[str, Any]] = dict(data.get("relations") or {})
        self.wing_defaults: Dict[str, str] = {
            str(k): str(v) for k, v in (data.get("wing_defaults") or {}).items()
        }
        self.known_entities: Dict[str, str] = {
            str(k): str(v) for k, v in (data.get("known_entities") or {}).items()
        }
        self.governance: Dict[str, Any] = dict(data.get("governance") or {})

        # alias → core type / relation
        self._type_alias: Dict[str, str] = {}
        for core, meta in self.entity_types.items():
            self._type_alias[_norm_key(core)] = core
            for a in meta.get("aliases") or []:
                self._type_alias[_norm_key(str(a))] = core

        self._rel_alias: Dict[str, str] = {}
        for core, meta in self.relations.items():
            self._rel_alias[_norm_key(core)] = core
            for a in meta.get("aliases") or []:
                self._rel_alias[_norm_key(str(a))] = core

        self._known_norm: Dict[str, Tuple[str, str]] = {}
        for name, typ in self.known_entities.items():
            self._known_norm[_norm_key(name)] = (name, typ)

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "MemoryOntology":
        p = Path(path) if path else default_ontology_path()
        data = _load_yaml(p)
        return cls(data, path=p)

    # ------------------------------------------------------------------ show
    def show(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "product": "ontology",
            "name": self.name,
            "version": self.version,
            "path": str(self.path) if self.path else None,
            "map_confidence_threshold": self.map_threshold,
            "entity_types": sorted(self.entity_types.keys()),
            "relations": sorted(self.relations.keys()),
            "wing_defaults": dict(self.wing_defaults),
            "known_entities_count": len(self.known_entities),
            "governance": self.governance,
            "message": (
                f"Ontology {self.name} v{self.version}: "
                f"{len(self.entity_types)} types, {len(self.relations)} relations"
            ),
        }

    # ------------------------------------------------------------------ validate
    def validate(self) -> Dict[str, Any]:
        errors: List[str] = []
        warnings: List[str] = []
        if not self.entity_types:
            errors.append("entity_types empty")
        if not self.relations:
            errors.append("relations empty")
        for t, meta in self.entity_types.items():
            if not isinstance(meta, dict):
                errors.append(f"entity_types.{t} must be a mapping")
                continue
            if not str(meta.get("description") or "").strip():
                warnings.append(f"entity_types.{t} missing description")
        for r, meta in self.relations.items():
            if not isinstance(meta, dict):
                errors.append(f"relations.{r} must be a mapping")
                continue
            for side in ("domain", "range"):
                vals = meta.get(side)
                if vals is None:
                    continue
                if not isinstance(vals, list):
                    errors.append(f"relations.{r}.{side} must be a list")
                    continue
                for t in vals:
                    if t not in self.entity_types:
                        errors.append(
                            f"relations.{r}.{side} references unknown type {t!r}"
                        )
        for name, typ in self.known_entities.items():
            if typ not in self.entity_types:
                errors.append(f"known_entities[{name!r}] unknown type {typ!r}")
        for t, wing in self.wing_defaults.items():
            if t not in self.entity_types:
                warnings.append(f"wing_defaults key {t!r} not in entity_types")
            if not wing:
                warnings.append(f"wing_defaults[{t}] empty")
        # require RELATED_TO and Entity as safety valves
        if "Entity" not in self.entity_types:
            errors.append("core type Entity is required")
        if "RELATED_TO" not in self.relations:
            warnings.append("RELATED_TO relation missing (soft links harder)")

        ok = not errors
        return {
            "ok": ok,
            "product": "ontology_validate",
            "path": str(self.path) if self.path else None,
            "version": self.version,
            "errors": errors,
            "warnings": warnings,
            "entity_type_count": len(self.entity_types),
            "relation_count": len(self.relations),
            "message": (
                "Ontology valid"
                if ok
                else f"Ontology invalid: {len(errors)} error(s)"
            ),
        }

    # ------------------------------------------------------------------ map type
    def resolve_type(
        self,
        label: Optional[str],
        *,
        confidence: Optional[float] = None,
        entity_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Map a free type label (and optional entity name) to a core type.

        Returns type, provisional, mapped_from, reason.
        """
        conf = float(confidence) if confidence is not None else None

        # 1) known entity name wins
        if entity_name:
            kn = self._known_norm.get(_norm_key(entity_name))
            if kn:
                canon_name, typ = kn
                return {
                    "type": typ,
                    "provisional": False,
                    "mapped_from": label or "unknown",
                    "reason": f"known_entity:{canon_name}",
                    "confidence": max(conf or 0.0, 0.9),
                }

        raw = (label or "").strip() or _DEFAULT_TYPE
        core = self._type_alias.get(_norm_key(raw))
        if core:
            meta = self.entity_types.get(core) or {}
            provisional = bool(meta.get("provisional_by_default"))
            if conf is not None and conf < self.map_threshold and core == _DEFAULT_TYPE:
                provisional = True
            # Weak confidence: only force provisional for types *not* in the
            # loaded ontology (YAML may define Concept, etc. beyond the old
            # hardcoded core set — AGY Grok handoff P6 fix).
            if (
                conf is not None
                and conf < self.map_threshold
                and core not in self.entity_types
            ):
                provisional = True
            return {
                "type": core,
                "provisional": provisional,
                "mapped_from": raw,
                "reason": "alias" if _norm_key(raw) != _norm_key(core) else "core",
                "confidence": conf,
            }

        # unknown free label
        return {
            "type": _DEFAULT_TYPE,
            "provisional": True,
            "mapped_from": raw,
            "reason": "unknown_type_provisional",
            "confidence": conf,
            "original_type": raw,
        }

    def resolve_relation(self, label: Optional[str]) -> Dict[str, Any]:
        raw = (label or "").strip() or _DEFAULT_REL
        core = self._rel_alias.get(_norm_key(raw))
        if core:
            return {
                "relation": core,
                "provisional": False,
                "mapped_from": raw,
                "reason": "alias" if _norm_key(raw) != _norm_key(core) else "core",
            }
        return {
            "relation": _DEFAULT_REL,
            "provisional": True,
            "mapped_from": raw,
            "reason": "unknown_relation_provisional",
            "original_relation": raw,
        }

    def wing_for(self, entity_type: str) -> Optional[str]:
        return self.wing_defaults.get(entity_type) or (
            (self.entity_types.get(entity_type) or {}).get("wing")
        )

    # ------------------------------------------------------------------ edge rules
    def edge_allowed(
        self,
        from_type: str,
        relation: str,
        to_type: str,
    ) -> Dict[str, Any]:
        rel_meta = self.relations.get(relation)
        if not rel_meta:
            # try resolve
            rr = self.resolve_relation(relation)
            relation = rr["relation"]
            rel_meta = self.relations.get(relation) or {}
            if rr.get("provisional") and not rel_meta:
                return {
                    "allowed": True,
                    "provisional": True,
                    "relation": relation,
                    "reason": "unknown_relation",
                }

        if rel_meta.get("always_allowed"):
            return {
                "allowed": True,
                "provisional": False,
                "relation": relation,
                "reason": "always_allowed",
            }

        domain = list(rel_meta.get("domain") or [])
        range_ = list(rel_meta.get("range") or [])
        # empty domain/range = any
        domain_ok = (not domain) or (from_type in domain) or (from_type == _DEFAULT_TYPE)
        range_ok = (not range_) or (to_type in range_) or (to_type == _DEFAULT_TYPE)

        if domain_ok and range_ok:
            # Entity as endpoint is softer
            provisional = from_type == _DEFAULT_TYPE or to_type == _DEFAULT_TYPE
            return {
                "allowed": True,
                "provisional": provisional,
                "relation": relation,
                "reason": "domain_range_ok" if not provisional else "entity_endpoint",
            }

        # violation → still allowed but provisional (hybrid policy)
        reasons = []
        if domain and from_type not in domain:
            reasons.append(f"domain expects {domain}, got {from_type}")
        if range_ and to_type not in range_:
            reasons.append(f"range expects {range_}, got {to_type}")
        return {
            "allowed": True,
            "provisional": True,
            "relation": relation,
            "reason": "domain_range_violation:" + "; ".join(reasons),
            "domain": domain,
            "range": range_,
        }

    # ------------------------------------------------------------------ normalize extract
    def normalize_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        e = dict(entity or {})
        name = str(e.get("name") or "").strip()
        conf = e.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else None
        except (TypeError, ValueError):
            conf_f = None
        resolved = self.resolve_type(
            str(e.get("type") or ""),
            confidence=conf_f,
            entity_name=name or None,
        )
        e["type"] = resolved["type"]
        # provisional if either extractor or ontology says so
        e["provisional"] = bool(e.get("provisional")) or bool(resolved["provisional"])
        if conf_f is not None and conf_f < self.map_threshold:
            e["provisional"] = True
        e["ontology"] = {
            "mapped_from": resolved.get("mapped_from"),
            "reason": resolved.get("reason"),
            "original_type": resolved.get("original_type"),
        }
        wing = self.wing_for(e["type"])
        if wing and not e.get("wing"):
            e["wing"] = wing
        return e

    def normalize_relation(self, rel: Dict[str, Any]) -> Dict[str, Any]:
        r = dict(rel or {})
        rr = self.resolve_relation(str(r.get("relation") or ""))
        r["relation"] = rr["relation"]
        # map endpoint types
        ft = self.resolve_type(
            str(r.get("from_type") or "Entity"),
            entity_name=str(r.get("from") or "") or None,
        )
        tt = self.resolve_type(
            str(r.get("to_type") or "Entity"),
            entity_name=str(r.get("to") or "") or None,
        )
        r["from_type"] = ft["type"]
        r["to_type"] = tt["type"]
        edge = self.edge_allowed(r["from_type"], r["relation"], r["to_type"])
        provisional = (
            bool(r.get("provisional"))
            or bool(rr.get("provisional"))
            or bool(ft.get("provisional"))
            or bool(tt.get("provisional"))
            or bool(edge.get("provisional"))
        )
        r["provisional"] = provisional
        r["ontology"] = {
            "relation_mapped_from": rr.get("mapped_from"),
            "relation_reason": rr.get("reason"),
            "edge_reason": edge.get("reason"),
            "original_relation": rr.get("original_relation"),
        }
        return r

    def normalize_extraction(
        self, extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Normalize entities + relations from cognify extract output."""
        out = dict(extracted or {})
        ents = [self.normalize_entity(e) for e in (out.get("entities") or [])]
        rels = [self.normalize_relation(r) for r in (out.get("relations") or [])]
        out["entities"] = ents
        out["relations"] = rels
        out["ontology_applied"] = True
        out["ontology_version"] = self.version
        out["provisional_entities"] = sum(1 for e in ents if e.get("provisional"))
        out["provisional_relations"] = sum(1 for r in rels if r.get("provisional"))
        return out

    def map_label(self, label: str, *, kind: str = "type") -> Dict[str, Any]:
        """CLI-friendly single label map."""
        kind = (kind or "type").lower()
        if kind in {"type", "entity", "entity_type"}:
            return {"ok": True, "kind": "type", **self.resolve_type(label)}
        if kind in {"relation", "rel", "edge"}:
            return {"ok": True, "kind": "relation", **self.resolve_relation(label)}
        return {
            "ok": False,
            "error": "kind must be type|relation",
            "error_code": "validation",
        }

    def induce_from_counts(
        self,
        type_counts: Dict[str, int],
        relation_counts: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """
        Offline 'induce' report: compare graph label frequencies to core vocab.
        Does not mutate the ontology (LLM induce is opt-in later).
        """
        unknown_types = []
        known = []
        for t, n in sorted((type_counts or {}).items(), key=lambda x: -x[1]):
            resolved = self.resolve_type(t)
            row = {"label": t, "count": n, **resolved}
            if resolved.get("reason") == "unknown_type_provisional" or (
                resolved.get("type") == _DEFAULT_TYPE and t != _DEFAULT_TYPE
            ):
                unknown_types.append(row)
            else:
                known.append(row)
        unknown_rels = []
        known_rels = []
        for r, n in sorted((relation_counts or {}).items(), key=lambda x: -x[1]):
            resolved = self.resolve_relation(r)
            row = {"label": r, "count": n, **resolved}
            if resolved.get("provisional"):
                unknown_rels.append(row)
            else:
                known_rels.append(row)
        return {
            "ok": True,
            "product": "ontology_induce",
            "mode": "counts_report",
            "message": (
                "Offline induce report (no ontology mutation). "
                "Review unknown_* lists before editing memory_ontology.yaml."
            ),
            "known_types": known[:50],
            "unknown_types": unknown_types[:50],
            "known_relations": known_rels[:50],
            "unknown_relations": unknown_rels[:50],
            "suggestion": (
                "Add high-frequency unknown labels as aliases under the "
                "closest core type/relation, then re-run validate."
            ),
        }

    def induce_from_texts(
        self,
        texts: Sequence[str],
        *,
        min_count: int = 2,
        top_n: int = 40,
    ) -> Dict[str, Any]:
        """
        MR-4: offline corpus induce beyond graph frequency report.

        Scans TitleCase / known multi-word tokens and relation verbs in free
        text, proposes alias candidates. Does **not** mutate YAML unless
        caller applies ``draft_aliases`` manually (or future LLM induce).
        """
        from collections import Counter

        type_counts: Counter = Counter()
        rel_counts: Counter = Counter()
        name_counts: Counter = Counter()
        title_re = re.compile(
            r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,3})\b"
        )
        verb_map = {
            "uses": "USES",
            "owns": "OWNS",
            "depends on": "DEPENDS_ON",
            "protects": "PROTECTS",
            "works with": "WORKS_WITH",
        }
        for raw in texts or []:
            t = raw or ""
            for m in title_re.finditer(t):
                name = m.group(1).strip()
                if len(name) < 2:
                    continue
                name_counts[name] += 1
                # if known entity, count its type
                kn = self._known_norm.get(_norm_key(name))
                if kn:
                    type_counts[kn[1]] += 1
                else:
                    type_counts["Entity"] += 0  # keep key space clean
            low = t.lower()
            for phrase, rel in verb_map.items():
                c = low.count(phrase)
                if c:
                    rel_counts[rel] += c

        # candidates: frequent names not already known
        alias_proposals = []
        for name, n in name_counts.most_common(top_n * 2):
            if n < min_count:
                continue
            if self._known_norm.get(_norm_key(name)):
                continue
            # skip pure stop-ish
            if name.lower() in {"the", "this", "that", "with", "from"}:
                continue
            alias_proposals.append(
                {
                    "name": name,
                    "count": n,
                    "suggested_type": "System" if n >= min_count + 1 else "Entity",
                    "action": "add_known_entity_or_alias",
                }
            )
            if len(alias_proposals) >= top_n:
                break

        base = self.induce_from_counts(dict(type_counts), dict(rel_counts))
        base["mode"] = "corpus_plus_counts"
        base["product"] = "ontology_induce_corpus"
        base["alias_proposals"] = alias_proposals
        base["name_frequency_top"] = [
            {"name": a, "count": b} for a, b in name_counts.most_common(20)
        ]
        base["draft_aliases"] = {
            p["name"]: p["suggested_type"] for p in alias_proposals[:20]
        }
        base["message"] = (
            "Offline corpus induce (no ontology mutation). "
            f"{len(alias_proposals)} alias proposal(s). "
            "Review draft_aliases before editing memory_ontology.yaml."
        )
        base["apply_hint"] = (
            "Opt-in only: merge draft_aliases into known_entities manually "
            "or via future `ontology induce --apply` (not default)."
        )
        return base


@lru_cache(maxsize=4)
def _cached_load(path_str: str) -> MemoryOntology:
    return MemoryOntology.load(Path(path_str) if path_str else None)


def get_ontology(path: Optional[str] = None) -> MemoryOntology:
    """Process-wide default ontology (cached by path)."""
    p = str(Path(path).resolve()) if path else str(default_ontology_path().resolve())
    return _cached_load(p)


def clear_ontology_cache() -> None:
    _cached_load.cache_clear()


def apply_ontology_to_extraction(
    extracted: Dict[str, Any],
    *,
    ontology: Optional[MemoryOntology] = None,
    enabled: bool = True,
) -> Dict[str, Any]:
    """Helper used by cognify; no-op when enabled=False."""
    if not enabled:
        out = dict(extracted or {})
        out["ontology_applied"] = False
        return out
    ont = ontology or get_ontology()
    return ont.normalize_extraction(extracted)
