# Improvement V5 — operational maturity

**Updated:** 2026-07-16  
**Status:** Sprints A–C **implemented** (code + unit tests)  
**After:** V4 + DoD-strict (already done)

## Goals

Strong · efficient · cost-optimized · flexible · complete — **depth & glue**, not new product surface spam.

## Sprint A — Trust & money truth

| ID | Item | DoD |
|----|------|-----|
| M1 | CLI/public spend middleware | `public_api.wrap` used on key CLI + MCP |
| M2 | MCP spend parity | `superai_run` / cli_run budget + contract |
| M4 | Accurate cost from registry | `cost_accounting.estimate` / `from_usage` |
| M5 | Error taxonomy | `error_code` on contracts |
| M7 | Security regression pack | tests in `test_improvement_v5.py` |

## Sprint B — Spend less, finish faster

| ID | Item | DoD |
|----|------|-----|
| M3 | Cooperative cancel | `CancelToken` in agent runtime |
| M6 | Idempotent writes | skip write if content unchanged |
| S1 | Cross-session result cache | opt-in `result_cache` |
| S2 | Adaptive escalate | quality fail → premium retry once |
| S4 | Smarter memory inject cap | rank + hard token budget helper |
| S7 | Board early-exit consensus | stop when first 2 agree |

## Sprint C — Ops & UX

| ID | Item | DoD |
|----|------|-----|
| M8 | Golden offline eval | `eval_golden` + tests |
| S3 | Run explain | `superai explain-run <run_id>` |
| S5 | Profile auto-suggest | from budget + history stats |
| S6 | Front-door confidence | low confidence flag + optional confirm |
| S10 | Progress snapshot | `superai progress` recent bus/trail |

## Verify

```powershell
pytest tests/test_improvement_v5.py -q
```
