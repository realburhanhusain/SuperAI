# Improvement V3 — Sprints A–D

**Updated:** 2026-07-16  
**Status:** A–D **implemented**  
**Smoke:** Phase 99 postponed  

| Sprint | Focus | % |
|--------|-------|--:|
| A | Tool protocol, failover, better diff, contracts | 100 |
| B | Cost on run, tenant write, goals safety, unit marker | 100 |
| C | Parallel board (prior), vision helpers, graph SVG, side-effect audit | 100 |
| D | Bandit pin, NL hooks, unit marker, tests | 100 |

## Commands

```powershell
superai agent-tools "read src/core/config.py and summarize" -m gpt-4o
superai agent-tui   # /tool … also model tool_call JSON via ask coding path
superai goals execute --max 2
superai bakeoff "hi" -m gpt-4o,deepseek-chat --pin
superai side-effects
pytest -m unit -q
# web: /graph (SVG)
```

## Verify

```powershell
pytest -m unit -q --tb=line
pytest tests/test_improvement_v3.py tests/test_sprint_abcd.py -q
```
