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

`tests/test_cost_accounting_m002.py`
