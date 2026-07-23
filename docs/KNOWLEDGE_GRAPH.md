# Knowledge Graph — Memory Roadmap P1

**Status:** Implemented (foundation)  
**Date:** 2026-07-23  
**Module:** `src/core/knowledge_graph.py`  
**CLI:** `superai kg …`  
**Roadmap:** `docs/MEMORY_ROADMAP_COGNEE_GAPS.md` (Gap 1)

## Spike decision (P0.1)

| Option | Decision |
|--------|----------|
| **A. Tables in same SQL stack as palace** | **Chosen** — SQLite file `~/.superai/memory/kg.sqlite` by default; optional Postgres via `SUPERAI_KG_DSN` / `SUPERAI_MEMORY_DSN` |
| B. Embedded graph engine (Kuzu) | Deferred — extra dependency |
| C. External Neo4j | Deferred — ops burden |

**Rationale:** SuperAI already standardizes on SQLAlchemy + SQLite/Postgres for Memory Palace. Co-locating the graph avoids a second service, keeps offline tests simple, and matches multi-session lock patterns (`kg.lock`).

**Non-goals for P1:** cognify/LLM extract, hybrid vector+graph recall, ontology validation (P2/P4/P6).

## Model

### Node (`kg_nodes`)

| Field | Meaning |
|-------|---------|
| `id` | Stable id (`n_…`) |
| `type` | Entity type (Person, System, Decision, …) |
| `name` | Display / lookup name |
| `properties` | JSON bag |
| `source_memory_id` | Optional link to `MemoryPalace` row |
| `dataset_id` | Namespace (default `default`) — P7 precursor |
| `wing` / `room` | Optional palace-aligned location |

### Edge (`kg_edges`)

| Field | Meaning |
|-------|---------|
| `from_id` → `to_id` | Directed edge |
| `relation` | Edge label |
| `weight` | Optional strength |
| `source_memory_id` | Provenance |
| `dataset_id` | Namespace |

Upsert key for edges: `(from_id, to_id, relation, dataset_id)`.

## Storage

| Env | Behavior |
|-----|----------|
| unset | `sqlite:///<home>/.superai/memory/kg.sqlite` |
| `SUPERAI_KG_DSN` | Explicit SQLAlchemy URL |
| `SUPERAI_MEMORY_DSN=postgresql…` | Reuse Postgres (tables `kg_*` only) |

Locks: `~/.superai/memory/kg.lock` (same file-lock helper as palace).

## CLI

```powershell
# Status
superai kg status
superai --json kg status

# Nodes
superai kg upsert-node "Cloud SQL" --type System --wing technical
superai kg query --type System --name "Cloud"
superai kg query --dataset d360

# Edges (creates missing nodes by name)
superai kg upsert-edge --from "Banking App" --to "Cloud SQL" --rel USES
superai kg upsert-edge --from "Cloud SQL" --to "Policy Tags" --from-type System --to-type RiskControl --rel PROTECTS

# Path (BFS, undirected, max hops)
superai kg path --from "Banking App" --to "Policy Tags" --hops 2
```

## Library

```python
from core.knowledge_graph import KnowledgeGraph, get_default_graph

kg = KnowledgeGraph()  # or SUPERAI_KG_DSN
kg.upsert_node(name="Alice", type="Person", dataset_id="d360")
kg.upsert_edge(from_name="Alice", to_name="Dataplex", relation="OWNS", to_type="System")
print(kg.path(from_name="Alice", to_name="Dataplex", hops=2))
print(kg.status())
```

## Relation to Memory Palace

- **Palace** = verbatim / embedding chunks (what was said or stored).  
- **Graph** = structured entities and relations (how things connect).  
- Link with `source_memory_id` when a node/edge is derived from a palace memory (cognify P2 will set this automatically).

## Tests

```powershell
pytest tests/test_knowledge_graph_p1.py -q
```

## Next (roadmap)

| Phase | Work |
|-------|------|
| P2 | Cognify: text → extract → upsert graph |
| P3 | Session buffer → promote into palace + optional graph |
| P4 | Hybrid / auto recall (vector + graph expand) |
| P6 | Ontology types for allowed relations |
| P7 | Dataset isolation productization |
