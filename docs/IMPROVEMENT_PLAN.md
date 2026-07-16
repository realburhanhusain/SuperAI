# SuperAI improvement plan — strengthen, efficiency, cost, flexibility, completeness

**Created:** 2026-07-16  
**Updated:** 2026-07-16 — Phases 1–5 implemented (basic); 6–7 partial/docs  
**Track:** `TASKBOARD.md`  
**Smoke:** Phase 99 still **POSTPONED**

## Progress dashboard

| Phase | Name | Tasks | Done | Status | % |
|------:|------|------:|-----:|--------|--:|
| 0 | Planning | 3 | 3 | complete | 100% |
| 1 | Trust & cost foundation | 6 | 6 | complete | 100% |
| 2 | Agent front door + sessions + permissions | 5 | 5 | complete | 100% |
| 3 | Catalog hygiene + profiles + cost report | 5 | 5 | complete | 100% |
| 4 | Routing efficiency (OW/local prefer) | 5 | 4 | basic done | 80% |
| 5 | Tool loop + health UX | 5 | 3 | basic done | 60% |
| 6 | NL + Windows polish | 4 | 1 | partial | 25% |
| 7 | Docs closeout | 3 | 3 | complete | 100% |
| 8 | Nice-to-have backlog | — | 0 | backlog | — |
| 99 | Live smoke | — | 0 | postponed | 0% |

**Phases 1–7 weighted estimate:** ~**85%** complete (core musts done; S1 streaming/board cache thinner).  
**Must-have (1–3):** **100%**.

## Delivered modules

| Module | Phase |
|--------|-------|
| `result_contract.py` | 1 |
| `permission_mode.py` | 2 |
| `ask_session.py` | 2 |
| `run_profiles.py` | 3 |
| `registry_validate.py` | 3 |
| `agent_tools.py` | 5 (minimal Read/Write/Glob jailed) |
| Orchestrator contract + budget hard-stop | 1 |
| multi_cli_board contract | 1 |
| Worker pool local/OW prefer via profile | 4 |
| CLI: default agent entry, profile, permission, cost footer | 2–3 |

## Commands

```powershell
superai                          # NL agent REPL
superai ask "…" --session ID --profile cheap --permission plan
superai run "…" --profile local-only --permission ask
superai profile cheap --persist
superai providers
```

## Remaining (optional follow-up)

- P4.3 Board subject cache (TTL)
- P5.3 Richer streaming events
- P5.4 Circuit-breaker detail in providers
- P6.2–P6.3 NL map + Windows probe polish
- Phase 8 nice-to-haves
- Phase 99 live smoke after all planned product work

## Resume

```text
1. docs/IMPROVEMENT_PLAN.md
2. TASKBOARD.md
3. Continue remaining Phase 4–6 polish OR new product track
4. No Phase 99 smoke yet
```
