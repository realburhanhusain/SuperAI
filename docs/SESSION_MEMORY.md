# Session Memory — Memory Roadmap P3 (end-to-end)

**Status:** Implemented  
**Date:** 2026-07-23  
**Module:** `src/core/session_memory.py`  
**CLI:** `superai memory-session …`  
**MCP:** `superai_session`  
**Depends on:** P1 graph, P2 cognify (optional on promote)  
**Roadmap:** `docs/MEMORY_ROADMAP_COGNEE_GAPS.md` (Gap 3)

## Spike decision (P0.3)

| Question | Decision |
|----------|----------|
| What is a session? | Explicit `session_id` with status `open \| ended \| cleared` |
| Where stored? | SQLite `~/.superai/memory/sessions.sqlite` (override `SUPERAI_SESSION_DSN`) |
| Palace pollution? | **Never** until promote / end auto-promote |
| Promote targets? | Memory Palace always (unless `--no-palace`); cognify graph opt-in; LearningEngine opt-in |
| LearningEngine relation? | Separate store; optional `--learning` on promote for task outcomes |

## End-to-end lifecycle

```text
  start session
       │
       ▼
  remember (notes / user / assistant / tool / pin)
       │
       ├─ recall  (lexical, session-scoped only)
       │
       ├─ pin     (durable mark)
       │
       ├─ promote → MemoryPalace (+ optional cognify → KG)
       │            (+ optional LearningEngine)
       │
       ├─ end     → auto-promote pinned + high-importance
       │
       └─ clear / purge-ttl
```

## CLI

```powershell
# Start
superai memory-session start --id demo1 --title "Outlook review" --dataset d360

# Buffer (not palace yet)
superai memory-session remember -s demo1 "User prefers SHA256 masking for PII" --importance 0.8 --pin
superai memory-session remember -s demo1 "scratch thought" --importance 0.2

# Isolated recall
superai memory-session recall -s demo1 "PII"
superai memory-session items -s demo1 --unpromoted

# Explicit promote → palace + graph
superai memory-session promote -s demo1 --min-importance 0.5 --cognify --cognify-mode mock

# End (auto-promote pins + importance ≥ 0.6)
superai memory-session end -s demo1
superai memory-session end -s demo1 --no-promote

# Housekeeping
superai memory-session clear -s demo1
superai memory-session purge-ttl --hours 72 --dry-run
superai memory-session status
superai --json memory-session list
```

## Promote policy

| Trigger | Behavior |
|---------|----------|
| `promote` | Selected items (or all matching filters) → palace |
| `promote --cognify` | Also run P2 cognify on each item content |
| `promote --learning` | Also LearningEngine.learn_from_task |
| `promote --pinned-only` | Only pinned items |
| `end` (default) | Promote **pinned** + items with `importance >= min` (default 0.6) |
| `end --no-promote` | Mark ended only |

Promoted items get `promoted=1` and `palace_memory_id` when palace write succeeds. Tags include `session`, `promoted`, `session:<id>`, `dataset:<id>`.

## Isolation guarantee

- `recall` / `items` filter strictly by `session_id`
- No cross-session leakage in default APIs
- Palace only receives data after promote/end

## MCP tools (P1+P3 thoroughness)

| Tool | Role |
|------|------|
| `superai_session` | start / remember / recall / promote / end / clear / status / list |
| `superai_kg_query` | status / query / path / neighbors |
| `superai_kg_upsert` | node / edge (mutating; plan mode blocked) |
| `superai_cognify` | text/file → graph |

## Library

```python
from core.session_memory import SessionMemory

sm = SessionMemory()
sm.start(session_id="s1", dataset_id="d360")
sm.remember("s1", "Decision: use PSC for Datastream", kind="decision", importance=0.9, pinned=True)
print(sm.recall("s1", "Datastream"))
print(sm.promote("s1", cognify_graph=True, cognify_mode="mock"))
print(sm.end("s1"))
```

## Storage

| Env | Default |
|-----|---------|
| `SUPERAI_SESSION_DSN` | `sqlite:///~/.superai/memory/sessions.sqlite` |
| Lock | `~/.superai/memory/sessions.lock` |

Tables: `sessions`, `session_items`.

## Tests

```powershell
pytest tests/test_session_memory_p3.py tests/test_cognify_p2.py tests/test_knowledge_graph_p1.py -q
```

Covers: isolation, promote→palace, promote+cognify, end auto-promote, clear, MCP tools.

## Honesty / safety

- Session buffer is local SQLite; not shared across machines until palace promote + sync
- Mutating MCP actions honor permission_mode (plan blocks promote/remember/clear)
- Cognify on promote defaults to **mock** unless `--cognify-mode llm`

## P1/P2 thoroughness notes

| Phase | Delivered end-to-end |
|-------|----------------------|
| **P1** | Graph store + CLI + path query + **MCP kg_query/kg_upsert** + tests + docs |
| **P2** | Mock+LLM cognify + file/dir batch + palace link + **MCP cognify** + tests + docs |
| **P3** | Full session lifecycle CLI + promote paths + MCP + tests + docs |

## Next

- **P4** auto/hybrid recall (`superai recall --strategy auto|session|graph|…`)
- **P8** agent-tui/MCP SessionEnd hooks calling `session.end`
