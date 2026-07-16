# Not-important polish pack (pre–live smoke)

**Updated:** 2026-07-16  

TUI depth polish pack (W1–W8). Remaining external gate for live multi-provider
verification is Phase 99 smoke (host/keys), not more not-important coding.

| ID | Item | Status |
|----|------|--------|
| W1 | Session export markdown | **[x]** `/export` + `AskSessionStore.export_markdown` |
| W2 | Session list + resume | **[x]** `/sessions` `/resume` |
| W3 | Undo last turn | **[x]** `/undo` |
| W4 | Cost/token session totals | **[x]** `/cost` + turn meta aggregation |
| W5 | Command palette + aliases | **[x]** `tui_commands` + `/commands` |
| W6 | Multi-line paste mode | **[x]** `/paste` … `/end` |
| W7 | VS Code extension depth | **[x]** ask / review / members / smoke-preflight |
| W8 | Smoke preflight checklist | **[x]** `smoke_preflight` + CLI (no false pass) |
| — | SuperAI multi-agent | **[x]** `docs/SUPERAI_AGENT.md` + `core.superai_agent` |

## Next

```powershell
superai smoke-preflight
superai smoke-preflight --readiness
# then live smoke when keys ready:
superai smoke-harness --allow-live
```

## Verify

```powershell
pytest tests/test_not_important.py -q
```
