# Not-important polish pack (pre–live smoke)

**Updated:** 2026-07-16  

The MoSCoW “not important” section was mostly **non-goals**. This pack turns the deferred
**“TUI depth instead of full OpenCode rewrite”** into concrete W1–W8 work so the only
remaining external gate is **live smoke (Phase 99)**.

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

## Explicit non-goals (still not done — by design)

| Item | Why |
|------|-----|
| Claim live smoke passed without keys | Honesty policy |
| Full OpenCode rewrite | **Done** — `docs/OPENCODE_REWRITE.md` + `core.opencode_agent` (post W1–W8) |

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
