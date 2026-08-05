# T07 — Config validation + diff helper

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[x]` |
| **Depends on** | T06 |
| **Estimate** | 1.5 h |
| **Owner** | self |

## Goal

Two pure functions in `core/config.py`, both with no side effects, so T09's
endpoint can validate before writing and preview before committing.

## Context

`Config` has no schema and no validation today — `.set()` (`config.py:231-237`)
accepts any key with any value. That is survivable from a CLI where a human
typed the key; it is not survivable from a form POST, where a typo silently
creates a dead key that nothing ever reads and the user believes they
configured something.

`DEFAULT_CONFIG` (`config.py:19-115`) is the de facto schema: it enumerates
every legitimate key and, by its values, the expected type of each.

## Part 1 — `validate_changes(changes: dict) -> list[str]`

Returns a list of human-readable problems; empty list means valid.

- **Unknown key** → reject. Anything absent from `DEFAULT_CONFIG` is a typo
  until proven otherwise. If a legitimate key is genuinely dynamic, add it to
  an explicit allowlist rather than weakening the rule.
- **Type mismatch** → reject, comparing against the type of the `DEFAULT_CONFIG`
  value. Careful with `bool`, which is a subclass of `int` in Python — check
  `bool` before `int` or `True` will pass as an integer field.
- **Range** → reject out-of-bounds values. **Read the actual keys in
  `DEFAULT_CONFIG` and derive the bounds from how the code uses them.** Do not
  guess from names. Likely candidates include an epsilon-style probability
  (0–1) and budget/limit fields (≥ 0), but confirm each before enforcing it.
- Messages must name the key and say what was wrong. `"invalid config"` is not
  an acceptable error string for a form UI.

## Part 2 — `diff_changes(changes: dict) -> str`

Returns a unified diff of the current config versus the config-as-it-would-be.

- Use `difflib.unified_diff` over the pretty-printed JSON of both states.
- **Writes nothing.** This is the function behind the preview; if it has side
  effects, the preview stops being a preview.
- Run the *would-be* state through `secrets.redact_obj` (`secrets.py:30-39`)
  before diffing, so a secret can never appear in a diff that gets rendered in a
  browser or pasted into a log.

## Acceptance criteria

- [x] `validate_changes` rejects unknown keys, wrong types, and out-of-range values, with a per-key message naming the key.
- [x] `bool` vs `int` is handled correctly (explicit test).
- [x] `diff_changes` returns a correct unified diff and **provably writes nothing** (assert file mtime and content unchanged after calling it).
- [x] Diff output is redacted.
- [x] Both functions are pure and independently unit-tested — no HTTP involved.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/ -k "config and (validate or diff)" -q
```

## Log

- Derived bounds from `DEFAULT_CONFIG` numeric fields:
  - Percentages (`bandit_epsilon`, `bandit_blend`): `0.0 <= v <= 1.0`
  - Budgets and positive counts (`budget_daily_usd`, `budget_run_usd`, `budget_daily_tokens`, `max_step_retries`, `max_replans`, `step_retry_backoff_sec`, `council_max_per_run`, `max_delegation_depth`): `v >= 0`
  - Minimum active pool counts (`worker_max`): `v >= 1`

Test verification:
```
$env:PYTHONPATH = "C:\tmp\superai-webui-t07\src"
python -m pytest tests/ -k "config and (validate or diff)" -q

.....                                                                    [100%]
5 passed, 1138 deselected, 1 warning in 33.52s
```
