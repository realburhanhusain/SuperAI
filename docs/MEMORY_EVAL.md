# Memory Roadmap Offline Eval

**Status:** Implemented  
**Date:** 2026-07-23  
**Module:** `src/core/memory_eval.py`  
**CLI:** `superai memory-eval`  
**Track:** Grok memory (post P1–P8) — **disjoint from AGY scorecard hardening**

## Purpose

Offline, no-network smoke that exercises Memory Roadmap verticals **P1–P8** in one isolated temp tree:

| Case ID | Phase | Check |
|---------|-------|--------|
| `p1_kg` | P1 | KG upsert + path |
| `p2_cognify` | P2 | Mock cognify graph write |
| `p3_session` | P3 | Session remember + recall |
| `p4_recall` | P4 | Keyword recall |
| `p5_ingest` | P5 | Markdown ingest → palace |
| `p6_ontology` | P6 | Ontology validate + type map |
| `p7_dataset` | P7 | Dataset isolation filter |
| `p8_capture` | P8 | Turn capture stream |

## CLI

```powershell
superai memory-eval
superai memory-eval --markdown
superai --json memory-eval
```

Exit code **1** if any case fails.

## Library

```python
from core.memory_eval import run_offline_memory_eval, report_markdown

rep = run_offline_memory_eval()
assert rep["ok"]
print(report_markdown(rep))
```

## Tests

`tests/test_memory_eval_offline.py`

## Non-goals

- Live LLM / provider smoke (Phase 99 host gate)  
- AGY scorecard modules  
- Performance benchmarks  

## Related

- Roadmap: `docs/MEMORY_ROADMAP_COGNEE_GAPS.md` (P1–P8 shipped; Phase 9+ backlog)  
- Capture: `docs/SESSION_CAPTURE.md`  
