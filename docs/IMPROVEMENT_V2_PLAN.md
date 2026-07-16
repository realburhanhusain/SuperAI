# Improvement V2 — Sprints A–D

**Updated:** 2026-07-16  
**Status:** A–D implemented (foundations)  
**Smoke:** Phase 99 postponed  

| Sprint | Focus | Status | % |
|--------|-------|--------|--:|
| A | Tools in TUI, git diff, fail-closed, contract | complete | 100 |
| B | Cost router, goals execute, smart compact, tenant filter | complete | 100 |
| C | Parallel board, cache normalize, vision msgs, pin, graph HTML, permissions on notify | complete | 100 |
| D | OpenRouter schedule, NL profile/yolo, PATH tests | complete | 100 |

**Overall A–D: 100%** (depth is vertical-slice; further polish optional)

## Commands

```powershell
superai agent-tui
# /tool read path=…
# /tool grep pattern=TODO
# /tool diff_apply (plan mode = dry-run)

superai goals execute --max 2
superai bakeoff "hi" -m gpt-4o,deepseek-chat --pin
superai models-refresh-openrouter --schedule
superai ask "use cheap mode and plan only: list models"
# web: /graph
```

## Verify

```powershell
pytest tests/test_sprint_abcd.py tests/test_phase8.py tests/test_result_contract.py -q
```
