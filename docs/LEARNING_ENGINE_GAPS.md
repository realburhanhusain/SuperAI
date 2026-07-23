# LearningEngine gaps — closed + honesty

**Updated:** 2026-07-24  
**Module:** `src/core/learning_engine.py`

## Observations → status

| Observation | Status |
|-------------|--------|
| Mid-task adaptation missing (only pre/post) | **Closed** — `learn_from_step` + `refresh_context_mid_task`; orchestrator calls both after each step |
| Conflict/distill only crude thresholds | **Improved** — entropy + multi-factor keep-score; Jaccard **or** embedding cosine distill + summary memory |
| Wings assignment try/except unreliable | **Closed earlier** — wings/room set in `MemoryPalace.store` from metadata |
| Hash embeddings silently look “semantic” | **Honest surface** — `embedding_backend_info()` / lifecycle status report hash vs ST; docs state quality impact |

## Mid-task APIs

```python
engine.learn_from_step(task, step_id, step_description, success=..., output=...)
engine.refresh_context_mid_task(task, recent_step_outputs=[...], task_type=...)
```

Orchestrator (`mid_task_memory_refresh=true` default): after every step → learn_from_step → refresh adaptive context for later steps.

## Conflict resolution

- Detect: success-rate **binary entropy**, severity high/medium/low, latency variance  
  (not embedding-based; hash vs ST does **not** change detect quality)  
- Resolve: keep highest `_memory_score` (importance + success + recency + feedback − latency); soft-demote diverse successes; **deprecate** failures/low scores  
- **Does not delete** palace rows  

## Distillation

- Within (task_type, model) groups: similarity clusters  
  - **embedding cosine** when non-hash backend  
  - **Jaccard** under hash embeddings  
- Deprecate near-duplicates only (rows retained); keep diverse high-score successes  
- Write a **distilled summary** memory (`phase=distill`)  
- No-op when `len(memories) < min_memories` or no group has ≥4 members — message explains why  

## Embeddings quality (Claude review validated)

| Mode | When | Impact |
|------|------|--------|
| Hash | No `sentence-transformers`, or `SUPERAI_EMBEDDING_HASH=1` | Weak near-dup / palace semantic search; conflict entropy unchanged |
| ST / Gemma | Package + model load succeed | Distill near-dup uses cosine; palace search higher quality |

## Wings

Reliably via `store(..., metadata={task_type, success, source})` → auto wing/room.
