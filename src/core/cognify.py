"""
Cognify pipeline (Memory Roadmap P0.2 → P2 / Cognee gap 2).

ECL-style flow:
  add (text/file) → extract (mock rules or LLM) → load (knowledge graph)
  optional: store a summary chunk in MemoryPalace with source_memory_id links

Default is **opt-in mock-safe**:
  - ``mode=mock`` / SUPERAI_MOCK_MODE / no API keys → rule-based extractor
  - ``mode=llm`` with keys → structured JSON extraction via ModelCaller
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Prefer longer known multi-word entities (matched first, high confidence)
_KNOWN_ENTITIES: List[Tuple[str, str]] = [
    ("Knowledge Catalog", "System"),
    ("Analytics Hub", "System"),
    ("Policy Tags", "RiskControl"),
    ("Banking App", "System"),
    ("Cloud SQL", "System"),
    ("BigQuery", "System"),
    ("Dataplex", "System"),
    ("PostgreSQL", "System"),
    ("Postgres", "System"),
    ("MemPalace", "System"),
    ("MemBrain", "System"),
    ("SuperAI", "System"),
    ("Grok", "System"),
    ("Claude", "System"),
]

# Relation verbs between tokens
_REL_VERBS: List[Tuple[str, str, Optional[str], Optional[str]]] = [
    (r"uses", "USES", "System", "System"),
    (r"owns", "OWNS", "Person", "System"),
    (r"depends on", "DEPENDS_ON", "System", "System"),
    (r"protects", "PROTECTS", "RiskControl", "System"),
    (r"works with", "WORKS_WITH", "Person", "Person"),
]

_IS_A_RE = re.compile(
    r"\b([A-Za-z][\w\-]+(?:\s+[A-Za-z][\w\-]+){0,3})\s+is a[n]?\s+"
    r"(Person|System|Dataset|Decision|RiskControl|Project|Document)\b",
    re.I,
)

_ENTITY_RE = re.compile(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+){0,2})\b")

_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.M)

_STOP = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "with",
    "from",
    "this",
    "that",
    "these",
    "those",
    "into",
    "using",
    "when",
    "where",
    "what",
    "which",
    "your",
    "our",
    "their",
    "also",
    "than",
    "then",
    "only",
    "more",
    "most",
    "such",
    "via",
    "per",
    "not",
    "yes",
    "no",
}


def _mock_mode_requested(mode: Optional[str] = None) -> bool:
    if mode:
        return str(mode).lower() in {"mock", "rules", "offline"}
    if (os.getenv("SUPERAI_MOCK_MODE") or "").lower() in {"1", "true", "yes"}:
        return True
    try:
        from .config import Config

        return bool(Config().use_mock)
    except Exception:
        return True


def _clean_name(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip(" \t\r\n.,;:\"'()[]{}"))
    return s[:120]


def extract_mock(text: str) -> Dict[str, Any]:
    """
    Rule-based extractor for offline / CI.

    Returns {entities: [{name,type,confidence}], relations: [{from,to,relation,confidence}]}
    """
    text = text or ""
    entities: Dict[str, Dict[str, Any]] = {}
    relations: List[Dict[str, Any]] = []

    def add_ent(name: str, typ: str = "Entity", conf: float = 0.55) -> None:
        name = _clean_name(name)
        if len(name) < 2:
            return
        if name.lower() in _STOP:
            return
        # reject pure type words as entities
        if name in {
            "Person", "System", "Dataset", "Decision",
            "RiskControl", "Project", "Document", "Entity", "Concept",
        }:
            return
        key = name.lower()
        prev = entities.get(key)
        if prev is None or conf > float(prev.get("confidence") or 0):
            entities[key] = {
                "name": name,
                "type": typ,
                "confidence": conf,
                "provisional": conf < 0.7,
            }

    # 1) Known multi-word entities first
    for name, typ in sorted(_KNOWN_ENTITIES, key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(name)}\b", text, re.I):
            # preserve canonical casing from catalog
            add_ent(name, typ, 0.85)

    # 2) Headings as concepts
    for h in _HEADING_RE.findall(text):
        add_ent(h, "Concept", 0.65)

    # 3) Title-case singles/phrases (weaker) — skip if already covered as known
    for m in _ENTITY_RE.finditer(text):
        cand = m.group(1)
        # skip fragments of known multi-word names
        if any(
            cand.lower() != kn.lower() and cand.lower() in kn.lower()
            for kn, _ in _KNOWN_ENTITIES
        ):
            continue
        add_ent(cand, "Entity", 0.5)

    # 4) Relation patterns using known names + simple Title tokens
    # Build alternation of known names + generic token
    known_alt = "|".join(
        re.escape(n) for n, _ in sorted(_KNOWN_ENTITIES, key=lambda x: -len(x[0]))
    )
    token = rf"(?:{known_alt}|[A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+){{0,2}})"
    for verb, rel, ft, tt in _REL_VERBS:
        pat = re.compile(rf"\b({token})\s+{verb}\s+({token})\b", re.I)
        for m in pat.finditer(text):
            a, b = _clean_name(m.group(1)), _clean_name(m.group(2))
            # map types from known catalog when possible
            ft_use, tt_use = ft or "Entity", tt or "Entity"
            for kn, kt in _KNOWN_ENTITIES:
                if a.lower() == kn.lower():
                    a, ft_use = kn, kt
                if b.lower() == kn.lower():
                    b, tt_use = kn, kt
            add_ent(a, ft_use, 0.8)
            add_ent(b, tt_use, 0.8)
            relations.append(
                {
                    "from": a,
                    "to": b,
                    "relation": rel,
                    "from_type": ft_use,
                    "to_type": tt_use,
                    "confidence": 0.8,
                    "provisional": False,
                }
            )

    for m in _IS_A_RE.finditer(text):
        a = _clean_name(m.group(1))
        typ = _clean_name(m.group(2))
        # prefer known casing
        for kn, _kt in _KNOWN_ENTITIES:
            if a.lower() == kn.lower():
                a = kn
                break
        add_ent(a, typ, 0.85)

    # Cap noise
    ent_list = sorted(entities.values(), key=lambda e: -float(e["confidence"]))[:80]
    rel_list = []
    seen = set()
    for r in relations[:80]:
        if not r["from"] or not r["to"] or r["from"].lower() == r["to"].lower():
            continue
        k = (r["from"].lower(), r["relation"], r["to"].lower())
        if k in seen:
            continue
        seen.add(k)
        rel_list.append(r)

    return {
        "ok": True,
        "mode": "mock",
        "entities": ent_list,
        "relations": rel_list,
        "extractor": "rules_v2",
    }


def extract_llm(text: str, *, model: Optional[str] = None) -> Dict[str, Any]:
    """LLM JSON extraction; falls back to mock on failure."""
    from .model_caller import ModelCaller
    from .model_registry import ModelRegistry

    prompt = (
        "Extract entities and relations from the text for a knowledge graph.\n"
        "Return ONLY valid JSON with keys entities and relations:\n"
        '{\"entities\":[{\"name\":\"...\",\"type\":\"Person|System|Dataset|Decision|'
        'RiskControl|Project|Document|Entity|Concept\",\"confidence\":0.0}],'
        '\"relations\":[{\"from\":\"...\",\"to\":\"...\",\"relation\":\"USES|OWNS|'
        'DEPENDS_ON|PROTECTS|WORKS_WITH|RELATED_TO|IS_A\",\"from_type\":\"...\",'
        '\"to_type\":\"...\",\"confidence\":0.0}]}\n'
        "Prefer precise names; do not invent facts not in the text.\n\n"
        f"TEXT:\n{(text or '')[:6000]}"
    )
    try:
        caller = ModelCaller(use_mock=False, registry=ModelRegistry())
        # pick a default cheap model if none
        m = model or os.getenv("SUPERAI_COGNIFY_MODEL") or "gpt-4o-mini"
        out = caller.call(model=m, prompt=prompt, skip_budget=False)
        raw = str(out.get("response") or out.get("content") or "")
        # find JSON object
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            fb = extract_mock(text)
            fb["mode"] = "llm_fallback_mock"
            fb["llm_error"] = "no_json"
            return fb
        data = json.loads(raw[start : end + 1])
        ents = data.get("entities") or []
        rels = data.get("relations") or []
        return {
            "ok": True,
            "mode": "llm",
            "entities": ents if isinstance(ents, list) else [],
            "relations": rels if isinstance(rels, list) else [],
            "extractor": "llm_json_v1",
            "model": m,
            "cost_source": out.get("cost_source"),
            "estimated_cost_usd": out.get("estimated_cost_usd"),
        }
    except Exception as e:  # noqa: BLE001
        fb = extract_mock(text)
        fb["mode"] = "llm_fallback_mock"
        fb["llm_error"] = str(e)[:300]
        return fb


def load_text_source(source: str) -> Dict[str, Any]:
    """Load text from a file path or treat as raw text."""
    p = Path(source)
    if p.is_file():
        try:
            body = p.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return {"ok": False, "error": str(e)[:300], "error_code": "io"}
        return {
            "ok": True,
            "text": body,
            "source_path": str(p.resolve()),
            "source_kind": "file",
        }
    if p.is_dir():
        return {
            "ok": False,
            "error": "directory not supported in single cognify; pass a file",
            "error_code": "validation",
        }
    return {
        "ok": True,
        "text": source,
        "source_path": None,
        "source_kind": "text",
    }


def cognify(
    source: str,
    *,
    dataset_id: str = "default",
    mode: Optional[str] = None,
    dry_run: bool = False,
    store_palace: bool = True,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    model: Optional[str] = None,
    kg: Any = None,
    palace: Any = None,
) -> Dict[str, Any]:
    """
    Run cognify on a text string or file path.

    Returns a report with extraction counts, graph writes, and optional palace id.
    """
    loaded = load_text_source(source)
    if not loaded.get("ok"):
        return loaded
    text = loaded.get("text") or ""
    if not text.strip():
        return {
            "ok": False,
            "error": "empty text",
            "error_code": "validation",
            "entities": 0,
            "relations": 0,
        }

    use_mock = _mock_mode_requested(mode)
    if use_mock:
        extracted = extract_mock(text)
    else:
        extracted = extract_llm(text, model=model)

    # P6: map free labels → core ontology (provisional on unknown / weak conf)
    try:
        from .ontology import apply_ontology_to_extraction

        apply_ont = True
        if (os.getenv("SUPERAI_ONTOLOGY") or "").strip().lower() in {
            "0",
            "false",
            "off",
            "no",
        }:
            apply_ont = False
        extracted = apply_ontology_to_extraction(extracted, enabled=apply_ont)
    except Exception as e:  # noqa: BLE001
        extracted = dict(extracted or {})
        extracted["ontology_applied"] = False
        extracted["ontology_error"] = str(e)[:200]

    entities = extracted.get("entities") or []
    relations = extracted.get("relations") or []

    report: Dict[str, Any] = {
        "ok": True,
        "product": "cognify",
        "mode": extracted.get("mode"),
        "extractor": extracted.get("extractor"),
        "source_kind": loaded.get("source_kind"),
        "source_path": loaded.get("source_path"),
        "dataset_id": dataset_id,
        "dry_run": bool(dry_run),
        "entities_found": len(entities),
        "relations_found": len(relations),
        "nodes_written": 0,
        "edges_written": 0,
        "palace_memory_id": None,
        "provisional": sum(1 for e in entities if e.get("provisional")),
        "ontology_applied": bool(extracted.get("ontology_applied")),
        "ontology_version": extracted.get("ontology_version"),
        "provisional_entities": extracted.get("provisional_entities"),
        "provisional_relations": extracted.get("provisional_relations"),
        "entities_sample": entities[:10],
        "relations_sample": relations[:10],
    }
    if extracted.get("ontology_error"):
        report["ontology_error"] = extracted["ontology_error"]
    if extracted.get("llm_error"):
        report["llm_error"] = extracted["llm_error"]
    if extracted.get("cost_source"):
        report["cost_source"] = extracted["cost_source"]
        report["estimated_cost_usd"] = extracted.get("estimated_cost_usd")

    if dry_run:
        report["message"] = (
            f"Dry-run: {len(entities)} entities, {len(relations)} relations "
            f"(mode={report['mode']})"
        )
        return report

    # Optional palace summary
    memory_id = None
    if store_palace:
        try:
            from .memory_palace import MemoryPalace

            mp = palace or MemoryPalace()
            summary = (
                f"[cognify] {loaded.get('source_path') or 'inline text'}\n"
                f"entities={len(entities)} relations={len(relations)} "
                f"mode={report['mode']}\n"
                f"{text[:800]}"
            )
            memory_id = mp.store(
                summary,
                tags=["cognify", f"dataset:{dataset_id}", report["mode"] or "mock"],
                metadata={
                    "source": "cognify",
                    "dataset_id": dataset_id,
                    "cognify_mode": report["mode"],
                    "entities_found": len(entities),
                    "relations_found": len(relations),
                },
                importance=0.65,
                wing=wing or "learning",
                room=room or "cognify",
            )
            report["palace_memory_id"] = memory_id
        except Exception as e:  # noqa: BLE001
            report["palace_error"] = str(e)[:200]

    # Load into graph
    try:
        from .knowledge_graph import KnowledgeGraph

        graph = kg or KnowledgeGraph()
        nw = ew = 0
        for e in entities:
            name = str(e.get("name") or "").strip()
            if not name:
                continue
            typ = str(e.get("type") or "Entity")
            props = {
                "confidence": e.get("confidence"),
                "provisional": bool(e.get("provisional")),
                "cognify": True,
            }
            if e.get("ontology"):
                props["ontology"] = e.get("ontology")
            node_wing = wing or e.get("wing")
            out = graph.upsert_node(
                name=name,
                type=typ,
                properties=props,
                source_memory_id=memory_id,
                dataset_id=dataset_id,
                wing=node_wing,
                room=room,
            )
            if out.get("ok"):
                nw += 1
        for r in relations:
            frm = str(r.get("from") or "").strip()
            to = str(r.get("to") or "").strip()
            rel = str(r.get("relation") or "RELATED_TO").strip() or "RELATED_TO"
            if not frm or not to:
                continue
            edge_props = {
                "confidence": r.get("confidence"),
                "provisional": bool(r.get("provisional")),
                "cognify": True,
            }
            if r.get("ontology"):
                edge_props["ontology"] = r.get("ontology")
            out = graph.upsert_edge(
                from_name=frm,
                to_name=to,
                from_type=str(r.get("from_type") or "Entity"),
                to_type=str(r.get("to_type") or "Entity"),
                relation=rel,
                properties=edge_props,
                source_memory_id=memory_id,
                dataset_id=dataset_id,
            )
            if out.get("ok"):
                ew += 1
        report["nodes_written"] = nw
        report["edges_written"] = ew
        report["kg_status"] = graph.status()
        report["message"] = (
            f"Cognified: {nw} nodes, {ew} edges "
            f"(found {len(entities)}/{len(relations)}; mode={report['mode']})"
        )
    except Exception as e:  # noqa: BLE001
        report["ok"] = False
        report["error"] = str(e)[:300]
        report["error_code"] = "graph_write"
        report["message"] = f"Graph write failed: {e}"[:200]

    return report


def cognify_paths(
    paths: Sequence[str],
    *,
    dataset_id: str = "default",
    mode: Optional[str] = None,
    dry_run: bool = False,
    store_palace: bool = True,
    glob_pat: str = "*.md",
) -> Dict[str, Any]:
    """Cognify one or more files; directories expand with ``glob_pat``."""
    files: List[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.rglob(glob_pat)))
        elif p.is_file():
            files.append(p)
        else:
            # treat as text only if single path
            if len(paths) == 1:
                return cognify(
                    raw,
                    dataset_id=dataset_id,
                    mode=mode,
                    dry_run=dry_run,
                    store_palace=store_palace,
                )
    results = []
    total_n = total_e = 0
    for f in files[:50]:
        r = cognify(
            str(f),
            dataset_id=dataset_id,
            mode=mode,
            dry_run=dry_run,
            store_palace=store_palace,
        )
        results.append(
            {
                "path": str(f),
                "ok": r.get("ok"),
                "nodes_written": r.get("nodes_written"),
                "edges_written": r.get("edges_written"),
                "mode": r.get("mode"),
            }
        )
        total_n += int(r.get("nodes_written") or 0)
        total_e += int(r.get("edges_written") or 0)
    return {
        "ok": all(x.get("ok") for x in results) if results else False,
        "product": "cognify_batch",
        "files": len(results),
        "nodes_written": total_n,
        "edges_written": total_e,
        "results": results,
        "message": f"Batch cognify: {len(results)} file(s), {total_n} nodes, {total_e} edges",
    }
