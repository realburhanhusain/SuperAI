# Learning lifecycle product surface (M061–M063)

**Updated:** 2026-07-24 (G1 product UX: dry-run, conflict UI, undeprecate)

SuperAI stores task outcomes as **learnings** in Memory Palace. This surface
covers the product UX for promoting durable patterns, resolving conflicts, and
distilling/deprecating redundant memories.

## Operator story (full loop)

```text
1. Outcomes write learnings     (agent/board success → learn_from_task / central write-back)
2. Review dashboard             superai learning status
3. Preview then promote         superai learning promote --dry-run
                                superai learning promote
4. Detect conflicts             superai learning conflicts
5. Resolve (or keep override)   superai learning conflicts --resolve
                                superai learning conflicts --resolve --keep <id>
6. Distill near-dups            superai learning distill --dry-run
                                superai learning distill
7. Inspect buckets              superai learning list --kind durable|deprecated|distilled
8. Soft undo deprecate          superai learning undeprecate <id>
```

**Write-back path (M057 adjacency):** successful SuperAI-mediated runs call
`central_memory.write_back` → `LearningEngine.learn_from_task` when learning
outcome is enabled. Those rows land with tag `learning` and become candidates
for `learning promote` once `importance` / success filters pass.

**Session buffer vs durable patterns:** `memory-session` promote is a *session*
buffer flush into the palace. `learning promote` is a *lifecycle* step that
marks high-value **already-stored learnings** as durable patterns. They are
related but not the same command.

## Commands

```powershell
# Dashboard — counts + top durable previews + embedding honesty
superai learning status

# List by bucket
superai learning list --kind active
superai learning list --kind durable -n 20
superai learning list --kind deprecated
superai learning list --kind distilled
superai learning list --kind all --type coding

# M061 — promote high-importance learnings to durable
superai learning promote --dry-run
superai learning promote
superai learning promote --min-importance 0.8 --limit 10
superai learning promote --id <memory-id>

# M062 — detect / resolve conflicts (Conflict UI)
superai learning conflicts
superai learning conflicts --resolve
superai learning conflicts --resolve --keep <memory-id>
superai learning conflicts --type coding

# M063 — distill near-duplicates + write summary memories
superai learning distill --dry-run
superai learning distill
superai learning distill --type coding --min-memories 5
superai learning distill --similarity-threshold 0.55

# Manual deprecate / soft restore (rows never deleted)
superai learning deprecate <memory-id> --reason "stale"
superai learning undeprecate <memory-id>

# Machine-readable (global flag)
superai --json learning status
superai --json learning promote --dry-run
```

Legacy commands still work: `superai learnings`, `superai conflicts`, `superai reflect --distill`.

## Lifecycle buckets

| Bucket | Meaning |
|--------|---------|
| **active** | Learning not durable and not deprecated |
| **durable** | Promoted pattern (`metadata.durable` / tag `durable`) |
| **deprecated** | Superseded, conflict-loser, or manual deprecate (**rows retained**) |
| **distilled** | Summary memory from `distill_knowledge` |

## Conflict UI (M062)

List mode (`learning conflicts`) shows per group:

- `task_type` / `model`
- entropy + severity (high/medium/low)
- success/fail counts
- `suggested_keep_id` (highest multi-factor score)
- `samples[]` with score factors (importance, success_boost, recency, …) and content previews

Resolve mode deprecates losers with `deletes_rows: false`. Each
`resolved_details` entry includes `kept_score_factors`, `deprecated_ids`, and
`soft_demoted_ids` (diverse high-score successes that were importance-demoted
only).

`--keep <id>` forces that memory as keeper when it appears in a conflict group.

## Distill defaults (M063)

| Knob | Default | CLI |
|------|---------|-----|
| `min_memories` | 5 | `--min-memories` |
| `similarity_threshold` | 0.55 | `--similarity-threshold` |
| Similarity method | embedding cosine if ST model; else **Jaccard** | reported in result |
| Group min size | 4 members per `(task_type, model)` | code |

`--dry-run` prints `preview_groups` (keep id, would-deprecate ids, method) and
does not mutate.

## Deprecate / undeprecate

- Deprecate sets `metadata.deprecated=true` + tag; **never deletes** the row.
- `learning list --kind deprecated` still finds them.
- `learning undeprecate <id>` clears the flag (soft undo). Importance is not
  automatically restored to pre-conflict values.

## API (library)

```python
from core.foundation_complete import (
    learning_lifecycle_status,
    learning_list,
    learning_promote_durable,
    learning_resolve_conflicts,
    learning_distill,
    learning_deprecate,
    learning_undeprecate,
)
```

Or via `LearningEngine`: `lifecycle_status()`, `list_lifecycle()`,
`promote_durable(dry_run=...)`, `resolve_conflicts(keep_memory_id=...)`,
`distill_knowledge(dry_run=..., similarity_threshold=...)`,
`deprecate_memory()`, `undeprecate_memory()`, `embedding_backend_info()`.

## Honesty (product quality, not just tests)

| Topic | Behavior |
|-------|----------|
| **Embeddings** | Default offline path often uses **hash embeddings** when `sentence-transformers` is not installed or `SUPERAI_EMBEDDING_HASH=1`. That is **not** a real semantic model — it weakens palace semantic search, clustering, and distill near-dup quality. |
| **Conflict detect** | Success-rate **binary entropy** per `(task_type, model)` — does **not** use vector similarity. |
| **Conflict resolve** | Keeps highest **multi-factor score**; **deprecates** lower scores (metadata + tags). **Does not delete rows.** |
| **Distill** | Near-dup via **embedding cosine** when a real ST model is loaded; else **Jaccard**. Requires enough learnings (`min_memories`, groups ≥4). May **no-op** with a clear `noop` / message. Deprecates dups; writes summary memory. |
| **Promote** | In-place update (`metadata.durable` + tag). `--dry-run` lists eligible/skipped without mutate. Failed outcomes and below-threshold importance are skipped with reasons. |
| **Enable real semantics** | `pip install sentence-transformers` (or `pip install -e ".[embeddings]"`), unset `SUPERAI_EMBEDDING_HASH`, optional `SUPERAI_EMBEDDING_MODEL=...`. |

`learning status` / `lifecycle_status()` expose `embedding` + `honesty` fields for operators.
CLI distill/conflicts results always include `embedding` when available.

## Verify

```powershell
pytest tests/test_learning_lifecycle_m061_m063.py tests/test_learning_engine_gaps.py tests/test_learning.py -q
superai learning status
superai learning promote --dry-run
superai learning conflicts
superai learning distill --dry-run
```
