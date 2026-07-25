# Improvement V4 — deepen SuperAI (strong / efficient / cost / flexible / complete)

**Updated:** 2026-07-16  
**Status:** Sprints A–C **implemented** + **DoD-strict sweep** (budget/contract all major spend paths, front-door CLI, local-first escalate, stream harden)  
**Smoke:** Phase 99 still host-gated (not this plan’s implementation)

### DoD-strict sweep (post A–C)

| Gap | Fix |
|-----|-----|
| Budget not on all spend paths | `spend_guard` on council, bakeoff, compare, HTTP `/api/superai/run`, agent |
| Contract not universal | `ensure_public_result` helper on those paths |
| Front door not wired | `superai` interactive + `superai do` + NL execute_intent re-route |
| Local-first escalate weak | `local_first.escalate_chain` in ModelCaller + worker pool |
| Stream empty-success | stream falls back to full `call()` if no chunks |

## Goals

| Goal | How V4 attacks it |
|------|-------------------|
| Strong | Contracts, readiness, run trail, safety tests |
| Efficient | Stream, step/tool cache, parallel tools, context budget |
| Cost-optimized | Budget hard enforcement, cheap-first, local-first, cost status |
| Flexible | Front-door policy, profiles, cancel/partial |
| Complete | Change-set apply, bandit feedback, classifier |

## Sprint A — Trust & cost (Must)

| ID | Item | DoD |
|----|------|-----|
| M1 | Budget on all spend paths | `budget_guard` soft API; agent + boards pre-check + record |
| M2 | Result contract everywhere public | Agent runtime + shared `ensure_contract` helper used on major paths |
| M3 | Fail-closed readiness before live agent | Live agent refuses if model not ready unless override |
| M4 | (Sprint B) real streaming hooks | Planned in B |
| M5 | (Sprint B) tool step cache | Planned in B |
| M6 | (Sprint B) cheap-first | Planned in B |
| M7 | Unified run trail | `run_trail` id links session + side effects + cost |
| M8 | Safety/money regression suite | `tests/test_improvement_v4.py` unit tests |

## Sprint B — Speed & spend

| ID | Item | DoD |
|----|------|-----|
| M4 | Provider stream API path | `ModelCaller.call_stream` generator + agent on_token |
| M5 | Tool result cache | Read tools cache by path+mtime |
| M6 | Cheap-first step types | Classifier routes summarize/plan to cheap members |
| S1 | Complexity → member count | Shared classifier used by boards |
| S6 | Local-first escalate | Profile + failover prefers local then premium |
| S8 | Parallel independent tools | Runtime batches read/grep/glob |
| S9 | `superai status --cost` | Snapshot budget + circuits + cache stats |

## Sprint C — Agent UX depth

| ID | Item | DoD |
|----|------|-----|
| S3 | Bandit feedback from runs | Success/latency/cost update bandit |
| S4 | Timeout / partial status | Runtime max_seconds → partial contract |
| S5 | Front-door policy map | `front_door` chooses agent vs board vs run |
| S7 | Context pack token budget | `context_pack` ordered drop under budget |
| S10 | Change-set apply/reject | Agent accumulates writes; `/apply` `/reject` |

## Verify

```powershell
pytest tests/test_improvement_v4.py -q
pytest -m unit -q --tb=line
```

## Commands (new)

```powershell
superai status --cost
superai agent "…" --permission plan
# agent TUI: /apply /reject after tool writes (Sprint C)
```
