# Memory Ontology — Memory Roadmap P6

**Status:** Implemented (hybrid controlled vocab)  
**Date:** 2026-07-23  
**Module:** `src/core/ontology.py`  
**Data:** `src/core/data/memory_ontology.yaml`  
**CLI:** `superai ontology show|validate|map|induce`  
**MCP:** `superai_ontology`  
**Depends on:** P1 knowledge graph; integrated into P2 cognify  
**Coordination:** Memory-only — does not touch AGY scorecard modules.

## Spike decision (P0.4)

| Choice | Decision |
|--------|----------|
| Model | **Hybrid** — fixed core types + aliases; free labels allowed |
| Unknown labels | Map to `Entity` / `RELATED_TO` with **`provisional=true`** (not hard-reject) |
| LLM induce | **Not auto** — offline `induce` reports frequencies only; file edits stay human/PR |
| Source of truth | `memory_ontology.yaml` (not hardcoded in cognify) |

## Core entity types

| Type | Examples | Default wing |
|------|----------|--------------|
| Person | owners, stewards, colleagues | people |
| System | Cloud SQL, Dataplex, SuperAI | technical |
| Dataset | BQ datasets, entry groups | technical |
| Decision | architecture choices | learning |
| RiskControl | Policy Tags, DLP | learning |
| Project | D360, SuperAI, LifeBrain | agentic |
| Document | demos, MRs, emails-as-refs | learning |
| Concept | headings / abstract topics | learning |
| Entity | generic fallback | learning |

## Core relations

`USES`, `OWNS`, `DEPENDS_ON`, `PROTECTS`, `WORKS_WITH`, `RELATED_TO`, `IS_A`, `PART_OF`

Domain/range constraints are enforced softly: violations still write edges but flag **`provisional=true`** with an ontology reason.

## Governance — who edits types?

1. **Canonical file:** `src/core/data/memory_ontology.yaml`  
2. **Owners:** SuperAI maintainers (see `governance.owners` in the YAML).  
3. **Change process:** edit YAML via PR; add aliases before inventing new core types.  
4. **Do not** hardcode new core types in `cognify.py` / `knowledge_graph.py` without updating YAML + tests.  
5. **Provisional policy:** unknown extract labels stay useful offline; review high-frequency provisional labels via `superai ontology induce` and promote to aliases.  
6. **Override path:** `SUPERAI_ONTOLOGY_PATH` points at an alternate YAML; `SUPERAI_ONTOLOGY=0` disables mapping in cognify.

## CLI

```powershell
superai ontology show
superai ontology validate
superai ontology map service --kind type
superai ontology map depends_on --kind relation
superai ontology induce --dataset default

# JSON
superai --json ontology validate
```

## Cognify integration

After mock/LLM extract, cognify runs `apply_ontology_to_extraction`:

- Type aliases → core types (`service` → `System`)
- Known entity names → preferred type (`Cloud SQL` → `System`)
- Weak confidence (`< map_confidence_threshold`, default 0.7) → provisional
- Edge domain/range check → provisional flag on properties
- Default wing from ontology when caller does not pass `--wing`

## Library

```python
from core.ontology import get_ontology, MemoryOntology

ont = get_ontology()
assert ont.validate()["ok"]
print(ont.resolve_type("policy"))  # RiskControl
print(ont.edge_allowed("Document", "PROTECTS", "System"))  # provisional
```

## MCP

Tool **`superai_ontology`**: `action=show|validate|map`, optional `label` + `kind` for map.

## Tests

`tests/test_ontology_p6.py` — file present, validate, aliases, known entities, edge provisional, normalize extract, cognify write path, disable env, induce report.

## Honest limits

- Induce does **not** rewrite YAML or call an LLM.  
- Domain/range never hard-blocks writes (bank demos stay resilient to noisy extract).  
- Requires **PyYAML** (`pyyaml` in package dependencies).
