# Multi-strategy Recall — Memory Roadmap P4

**Status:** Implemented  
**Date:** 2026-07-23  
**Module:** `src/core/recall_router.py`  
**CLI:** `superai recall`  
**MCP:** `superai_memory_search` (now multi-strategy; default `auto`)  
**Depends on:** P1 graph, P2 cognify (data), P3 session  
**Coordination:** Lives only in memory-recall modules — does not modify scorecard / exit-codes / git-helpers / prompt-injection work.

## Strategies

| Strategy | Behavior |
|----------|----------|
| `vector` | MemoryPalace semantic search |
| `keyword` | Token/tag lexical scan over palace |
| `graph` | KG name match + 1-hop neighbors |
| `hybrid` | Vector + graph + keyword merge (default for many auto cases) |
| `session` | Session buffer only; **fallthrough to hybrid** if empty (unless `--no-fallthrough`) |
| `auto` | Heuristic pick (always reports `strategy` + `strategy_reason`) |

## Auto heuristics

| Signal | Pick |
|--------|------|
| “related / connected / depends / who owns / path” | hybrid |
| “this session / prefer / last time” + `--session` | session |
| Quoted phrase or `ABC-123` ticket shape | keyword |
| Short query + session id | session first |
| Default | hybrid |

## CLI

```powershell
superai recall "Cloud SQL" --strategy auto
superai recall "related to Banking App" --strategy hybrid
superai recall "prefer dark mode" --strategy session -s demo1
superai recall "ABC-123" --strategy keyword
superai --json recall "Policy Tags" -S graph --dataset default
```

## Library

```python
from core.recall_router import recall

out = recall("related to Cloud SQL", strategy="auto", top_k=10)
print(out["strategy"], out["strategy_reason"], out["count"])
for h in out["hits"]:
    print(h.get("source"), str(h.get("content"))[:80])
```

## Honesty

Every response includes:

- `strategy` — what actually ran (`session+hybrid` if fallthrough)
- `strategy_requested` — user input
- `strategy_reason` — why auto chose it
- `notes` — optional counts / fallthrough info

## Tests

```powershell
pytest tests/test_recall_router_p4.py -q
```

## Next

- P5 multi-format ingest into cognify  
- P6 ontology filters on graph edges  
- P7 dataset-scoped recall defaults  
- P8 agent SessionEnd → session.end  
