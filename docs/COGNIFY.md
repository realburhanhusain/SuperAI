# Cognify — Memory Roadmap P2

**Status:** Implemented (mock-first + optional LLM)  
**Date:** 2026-07-23  
**Module:** `src/core/cognify.py`  
**CLI:** `superai cognify`  
**Depends on:** P1 knowledge graph (`docs/KNOWLEDGE_GRAPH.md`)  
**Roadmap:** `docs/MEMORY_ROADMAP_COGNEE_GAPS.md` (Gap 2)

## Spike decision (P0.2)

| Choice | Decision |
|--------|----------|
| Extractor | **Hybrid:** rule-based mock (`rules_v2`) offline; optional LLM JSON extract when `--mode llm` + keys |
| Always-on? | **No** — opt-in CLI; default `--mode mock` |
| Palace write | Optional summary chunk with tags `cognify` + dataset (disable with `--no-palace`) |
| Fail mode | LLM errors fall back to mock extractor; empty text fails closed |

## Pipeline (ECL)

```text
  source (text | file | dir/*.md)
       │
       ▼
  extract  ── mock rules  OR  LLM JSON ──► entities + relations
       │
       ├─ (optional) MemoryPalace.store summary → memory_id
       │
       ▼
  load  ── KnowledgeGraph.upsert_node / upsert_edge
       │     (source_memory_id linked when palace used)
       ▼
  report (counts, mode, samples)
```

## CLI

```powershell
# Offline-safe (default)
superai cognify "Banking App uses Cloud SQL." --mode mock
superai cognify .\docs\KNOWLEDGE_GRAPH.md --mode mock --dataset superai
superai cognify .\docs --glob "*.md" --mode mock --dry-run

# Live LLM extract (needs keys + budget)
superai cognify .\notes.md --mode llm --dataset d360

# JSON automation
superai --json cognify "Policy Tags protects Cloud SQL." --mode mock --no-palace
```

| Flag | Meaning |
|------|---------|
| `--mode mock\|llm` | Extractor (default **mock**) |
| `--dataset` | Graph + palace dataset namespace |
| `--dry-run` | Extract only; no writes |
| `--no-palace` | Skip MemoryPalace summary |
| `--glob` | When source is a directory (default `*.md`) |

## Library

```python
from core.cognify import cognify, extract_mock
from core.knowledge_graph import KnowledgeGraph

print(extract_mock("Cloud SQL uses Dataplex."))
kg = KnowledgeGraph()
report = cognify(
    "Alice owns Banking App. Banking App uses Cloud SQL.",
    mode="mock",
    dataset_id="demo",
    store_palace=False,
    kg=kg,
)
print(report["message"], kg.path(from_name="Alice", to_name="Cloud SQL", hops=2))
```

## Mock extractor notes

- Prefers **known multi-word** entities (Cloud SQL, Policy Tags, Banking App, …)
- Relation verbs: uses, owns, depends on, protects, works with
- Type hints via `is a System|Person|…`
- Title-case phrases as weaker provisional entities
- Cap 80 entities / 80 relations per run

## Honesty

- Report always includes `mode` (`mock` | `llm` | `llm_fallback_mock`)
- LLM path records `cost_source` / `estimated_cost_usd` when available
- Dry-run never mutates graph or palace

## Tests

```powershell
pytest tests/test_cognify_p2.py tests/test_knowledge_graph_p1.py -q
```

## Next

| Phase | Work |
|-------|------|
| P3 | Session memory buffer + promote |
| P4 | Auto/hybrid recall (vector + graph) |
| P5 | PDF / URL ingest into cognify |
| P6 | Ontology allow-list for relation types |
