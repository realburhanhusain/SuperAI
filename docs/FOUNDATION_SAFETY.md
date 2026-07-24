# Foundation safety — M001 / M008 / M018

Closes the residual “everywhere” gaps for D360-grade SuperAI use: hard budget
ceilings, stable result envelopes, and mandatory subprocess timeouts.

## Status

| ID | Intent | Proof |
|----|--------|-------|
| **M001** | Hard budget ceilings on every spend path | `ModelCaller.call` always runs `call_lifecycle.pre_call` → `spend_guard.budget_precheck` (unless mock / explicit `skip_budget`). Boards/MCP/HTTP add prechecks. Exhaustive registry: `foundation_safety.SPEND_PATHS`. Audit: `audit_m001()`. |
| **M008** | Stable result contract on every public / TUI command | `ensure_public_result` / `emit_public` / `tui_envelope`. All interactive TUI slash handlers (`/mux`, `/pmux`, `/vim`, `/mouse`, `/a11y`, native) return `contract: superai.result.v1`. Audit: `audit_m008()`. |
| **M018** | Timeouts on model, CLI, and tool ops | `model_timeouts.run_with_timeout` on model calls; `tool_timeouts` registry; **`subprocess_safety.run`** for finite host/git/rclone/etc. Long-lived panes/daemon are allowlisted. Audit: `audit_m018()` + static inventory. |

## Commands

```powershell
# Offline exhaustive audit (used in tests)
python -c "from core.foundation_safety import audit_all; import json; print(json.dumps(audit_all(), indent=2, default=str))"

# Subprocess inventory only
python -c "from core.subprocess_safety import inventory_subprocess_sites; print(inventory_subprocess_sites())"

# CLI (if registered)
superai foundation-safety
```

## Stage I1 Residual Safety Evidence (2026-07-24)

- **Fail-Closed Budget Precheck (`src/core/spend_guard.py:44`):** When budget enforcement is active (`enforce=True`), exceptions during precheck fail closed with `ok: False`, `blocked: True`, and `error_code: "budget_internal"`.
- **Live Stream Budget Gate (`src/core/model_caller.py:133`):** `call_stream()` invokes `pre_call()` prior to initializing live SSE provider requests. Exceeded budgets set stream metadata to `mode="budget_blocked"`.
- **MCP Safety Matrix (`src/core/mcp_safety.py:13,268`):** 24/24 registered tools classified (`spend=4`, `mutate=11`, `unmapped=0`), with `superai_ask_session` and `superai_cli_parallel` added to `SPEND_TOOLS`.
- **TOP_30 Invocation Depth (`src/core/public_surface.py:265` & `tests/test_agy_i1_residuals.py`):** Verified offline contract checks and TOP_30 invocation coverage.

## TUI envelopes (M008)

Interactive handlers must return dicts with at least:

- `ok`, `status`, `contract` (`superai.result.v1`)
- `mock` / `dry_run` honesty fields
- `handled` for slash routing

Helper: `foundation_safety.tui_envelope(result)`.

## Subprocess timeouts (M018)

```python
from core.subprocess_safety import run, run_result

run(["git", "status"], kind="git")           # timeout from tool_timeouts
run_result(["rclone", "ls", "x:"], kind="rclone")  # contract envelope
```

**Allowlisted long-lived** (no wall-clock kill of the whole process):

- `goals_daemon` background `Popen`
- `tui_process_mux` interactive panes / ConPTY

## Tests

- `tests/test_foundation_safety_m001_m008_m018.py` — exhaustive offline proof
- Existing `test_foundation_complete_must.py`, `test_foundation_lift.py`, `test_result_contract.py`

## Scorecard

Improved scorecard marks M001 / M008 / M018 complete when `audit_all().ok`
and the dedicated tests pass. Immutable `V1_V6_UNIFIED_SCORECARD.md` is not
bulk-edited.
