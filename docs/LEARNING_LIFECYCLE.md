# Learning lifecycle product surface (M061–M063)

**Updated:** 2026-07-23  

SuperAI stores task outcomes as **learnings** in Memory Palace. This surface
covers the product UX for promoting durable patterns, resolving conflicts, and
distilling/deprecating redundant memories.

## Commands

```powershell
# Dashboard — counts + top durable previews
superai learning status

# List by bucket
superai learning list --kind active
superai learning list --kind durable -n 20
superai learning list --kind deprecated
superai learning list --kind distilled
superai learning list --kind all --type coding

# M061 — promote high-importance learnings to durable
superai learning promote
superai learning promote --min-importance 0.8 --limit 10
superai learning promote --id <memory-id>

# M062 — detect / resolve conflicts
superai learning conflicts
superai learning conflicts --resolve

# M063 — distill near-duplicates + write summary memories
superai learning distill
superai learning distill --type coding --min-memories 5

# Manual deprecate
superai learning deprecate <memory-id> --reason "stale"

# Machine-readable (global flag)
superai --json learning status
```

Legacy commands still work: `superai learnings`, `superai conflicts`, `superai reflect --distill`.

## Lifecycle buckets

| Bucket | Meaning |
|--------|---------|
| **active** | Learning not durable and not deprecated |
| **durable** | Promoted pattern (`metadata.durable` / tag `durable`) |
| **deprecated** | Superseded, conflict-loser, or manual deprecate |
| **distilled** | Summary memory from `distill_knowledge` |

## API (library)

```python
from core.foundation_complete import (
    learning_lifecycle_status,
    learning_list,
    learning_promote_durable,
    learning_resolve_conflicts,
    learning_distill,
    learning_deprecate,
)
```

Or via `LearningEngine`: `lifecycle_status()`, `list_lifecycle()`, `promote_durable()`,
`resolve_conflicts()`, `distill_knowledge()`, `deprecate_memory()`.

## Honesty

- Offline/unit tests use hash embeddings + local Memory Palace.
- Conflict resolve deprecates **lower multi-factor scores**; it does not delete rows.
- Distill requires enough similar learnings; may no-op with a clear message.

## Verify

```powershell
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_learning_engine_gaps.py -q
```
