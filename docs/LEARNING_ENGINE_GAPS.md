# LearningEngine gaps — closed

**Updated:** 2026-07-15  
**Module:** `src/core/learning_engine.py`

## Observations → status

| Observation | Status |
|-------------|--------|
| Mid-task adaptation missing (only pre/post) | **Closed** — `learn_from_step` + `refresh_context_mid_task`; orchestrator calls both after each step |
| Conflict/distill only crude thresholds | **Improved** — entropy + multi-factor keep-score; Jaccard near-duplicate distill + summary memory |
| Wings assignment try/except unreliable | **Closed earlier** — wings/room set in `MemoryPalace.store` from metadata (no separate try-path in learn) |

## Mid-task APIs

```python
engine.learn_from_step(task, step_id, step_description, success=..., output=...)
engine.refresh_context_mid_task(task, recent_step_outputs=[...], task_type=...)
```

Orchestrator (`mid_task_memory_refresh=true` default): after every step → learn_from_step → refresh adaptive context for later steps.

## Conflict resolution

- Detect: success-rate **binary entropy**, severity high/medium/low, latency variance  
- Resolve: keep highest `_memory_score` (importance + success + recency + feedback − latency); soft-demote diverse successes; hard-deprecate failures/low scores  

## Distillation

- Within (task_type, model) groups: **Jaccard** similarity clusters  
- Deprecate near-duplicates only; keep diverse high-score successes  
- Write a **distilled summary** memory (`phase=distill`)  

## Wings

Reliably via `store(..., metadata={task_type, success, source})` → auto wing/room.
