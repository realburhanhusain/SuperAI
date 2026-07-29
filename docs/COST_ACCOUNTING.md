# Cost accounting (M002)

Accurate spend truth: **real usage tokens × registry rates**, with honest estimate fallbacks.

## Rules

| Situation | Behavior | `cost_source` |
|-----------|----------|---------------|
| Provider returned usage | Price prompt/completion (or total) × registry rate | `usage` |
| No usage on result | Estimate tokens from prompt/response length | `estimate` |
| `cli:*`, ollama/local | Always $0 | `zero_local` |
| Board / multi-member | Sum member costs via `aggregate_costs` | `usage` / `mixed` / `estimate` |

## Registry rates

- Primary: `ModelInfo.cost_per_1k_tokens` from `config/models.json` (blended).
- Optional split (if present on model `extra` or future JSON fields):
  - `input_cost_per_1k` / `output_cost_per_1k`
- If the model is missing from the registry, a small heuristic rate is used and
  `pricing_source` is `heuristic` (not claimed as metered).

## API

```python
from core.cost_accounting import (
    from_usage,
    estimate_call,
    attach_cost_fields,
    aggregate_costs,
    audit_m002,
)

from_usage("gpt-4o", prompt_tokens=100, completion_tokens=50)
estimate_call("gpt-4o", "long prompt…")
attach_cost_fields(result, model="gpt-4o", prompt=prompt)  # used by post_call
aggregate_costs(list_of_member_results)  # council / multi-CLI
```

## Integration points

- `call_lifecycle.post_call` → `attach_cost_fields` (every `ModelCaller` path)
- `council` → aggregates proposals/critiques/decision costs
- `multi_cli_advisory` → aggregates opinion costs
- `superai foundation-check M002` → offline audit

## Tests

`tests/test_cost_accounting_m002.py` · `tests/test_estimate_source.py`

---

# `estimate_source` — the one field to read (V1-P1-4)

The two fields above answer different questions: `cost_source` says where the
**tokens** came from, `pricing_source` says where the **rate** came from. A
consumer had to know both, and how they combine, to tell a metered figure from
a guessed one. A third name, `estimate_source`, existed on exactly one contract
(`board_preflight`) and reported `pricing_source`'s vocabulary.

`estimate_source` is now canonical, with three values ordered by trust.

| `estimate_source` | Meaning | Trust |
|---|---|---|
| **`actual`** | Metered provider usage priced from the registry — or a genuine `$0` for a local/CLI model, where nothing was estimated | Highest |
| **`registry`** | Token count *estimated*, but priced with real registry rates | Medium |
| **`fallback`** | Heuristic rates; model not in the registry. An order of magnitude, not a price | Lowest |

On any aggregate the **weakest link wins** — one `fallback` row makes the whole
total `fallback`, because a sum is only as honest as its worst term.

```python
from core.cost_accounting import resolve_estimate_source
```

- `zero_local` on either field → `actual`
- `cost_source == "usage"` → `actual`
- `pricing_source` in `registry` / `registry_io` → `registry`
- otherwise → `fallback`

`cost_source` and `pricing_source` are still emitted unchanged; they are simply
no longer the fields to reason about.

## Pre-flight estimates now use the registry

`budget_precheck` used a flat **0.1 USD / 500 tokens** for every command, so a
ceiling check against a local CLI model and one against Opus saw the same
number. Naming a model prices it properly:

```python
budget_precheck(model="gpt-4o", tokens=1000, command_name="council")
```

| Call | Estimate | `estimate_source` |
|---|---|---|
| `estimate_for_model("gpt-4o", tokens=1000)` | `0.005` from registry rate | `registry` |
| `estimate_for_model("cli:claude", tokens=1000)` | `0.0` | `actual` |
| `estimate_for_model("unknown-model", tokens=1000)` | heuristic rate | `fallback` |
| `estimate_for_model(None)` | `DEFAULT_ESTIMATE_USD` (0.1) | `fallback` |

**Backwards compatible.** `estimated_usd` defaults to `None` rather than `0.1`.
An explicit estimate still wins, and a caller passing neither model nor
estimate gets the old constant — existing call sites behave exactly as before,
but are now honestly labelled `fallback` instead of implying precision.

## Reading a cost in automation

```python
cost = result.get("estimated_cost_usd")
match result.get("estimate_source"):
    case "actual":   ...  # safe to bill or report
    case "registry": ...  # safe to gate on; token count is approximate
    case "fallback": ...  # order of magnitude only — never report as a price
```

## Where it appears

- `from_usage` and everything built on it (`from_result`, `estimate_call`,
  `attach_cost_fields`)
- `aggregate_costs` — weakest link across rows
- `spend_guard.estimate_for_model`, and blocked `budget_precheck` envelopes
- `board_preflight.estimate_board` — weakest link across **all** members.
  This previously read `per[0]["pricing_source"]`, so a five-member board
  containing one unpriced model advertised a registry-grade estimate.

