# T12 — `GET` / `POST /api/models`

| | |
|---|---|
| **Wave** | W3 |
| **Status** | `[ ]` |
| **Depends on** | T08, T09 |
| **Estimate** | 1.5 h |
| **Owner** | — |

## Goal

Let the model registry be inspected and edited from the browser — the surface
where "simplify SuperAI configuration" pays off most, since registry rows are
exactly what a user tweaks when adding a provider or a `cliproxy:` model.

## Context

- `core.model_registry.ModelRegistry` (`model_registry.py:53-`) is **read-only
  today**. There is no write path anywhere in that module; you are adding the
  first one.
- Load precedence (`model_registry.py:36-44`):
  1. `~/.superai/config/models.json`  ← **the only legitimate write target**
  2. repo `config/models.json`
  3. `src/config/models.json`
  4. `./config/models.json`
- `ModelInfo` fields at `model_registry.py:21-33`. Note `:26`: `api_key_env`
  stores an env var **name**, never a secret value. That is a real structural
  advantage over CLIProxyAPI's `config.yaml`, which stores keys inline — SuperAI's
  registry can be shown in a browser without redacting credentials, because it
  never held any.

## Constraint C2 is the whole task

**Writes go to `~/.superai/config/models.json` and nowhere else.** Writing to
the repo copy would mutate a git-tracked file from a running server — silently
dirtying the working tree of whichever of the ~10 concurrent worktrees happened
to be checked out. Enforce this in code, not by convention, and prove it in a
test.

## Steps

1. `GET /api/models` — return the merged, resolved registry, and **say which
   file each row came from**. Precedence is invisible otherwise, and "I edited
   models.json and nothing changed" is the predictable support question.
2. `POST /api/models` — validate every row against `ModelInfo`'s fields before
   writing. Reject unknown fields and wrong types, in the spirit of T07.
3. Reuse T06's atomic-write-plus-backup mechanism. Do not write a second,
   subtly different implementation — extract a shared helper if needed.
4. Audit-log the write (T09's pattern).
5. Both routes management-token gated, both behind the feature flag (T08).
6. If the user-level file does not exist yet, create it with the edited rows
   only — do **not** copy the whole merged registry down into it, or every
   future repo-side registry update becomes invisible to that user.

## Acceptance criteria

- [x] `GET /api/models` returns the registry with per-row provenance.
- [x] `POST` validates against `ModelInfo`; invalid rows refused, nothing written.
- [x] **Test proves the repo-tracked `config/models.json` is byte-identical after a POST** (hash before/after, fake `HOME`).
- [x] Write is atomic and backed up.
- [x] First write creates the user-level file containing only user rows, not a flattened copy of everything.
- [x] Audit entry recorded.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k models -q
git status --porcelain config/    # must print nothing after the test run
```

## Log

```
...                                                                      [100%]
3 passed, 22 deselected in 1.95s
```
