# T11 — `GET /api/audit`

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[ ]` |
| **Depends on** | T08 |
| **Estimate** | 30 min |
| **Owner** | — |

## Goal

Surface the audit trail in the console, so config changes made through the
browser are visible and attributable.

## Context

- `core.audit_log.AuditLog.recent(limit)` at `src/core/audit_log.py:38-48`
  already reads back `~/.superai/audit.jsonl`.
- Entries are **already redacted at write time** (`audit_log.py:32` runs
  `detail` through `secrets.redact_obj`). Do not assume that means every field
  is safe — read what `record()` actually stores before rendering it.

## Why this needs the management token, not the read token

Once T09 lands, the audit log becomes a record of configuration history: what
was changed, by which actor, and when. Even fully redacted, that reveals write
intent and timing — useful to an attacker profiling the system, and not
something a plain status reader needs.

Gate it with `SUPERAI_WEB_MANAGEMENT_TOKEN` (T08), not `SUPERAI_WEB_TOKEN`.

**Consequence for T05:** the `/console` page must degrade gracefully when the
management token is absent — show the panel as "requires management token"
rather than an error. Most users will run the console read-only.

## Steps

1. Add `@app.get("/api/audit")` with a `limit` query param (sane default, e.g.
   50; enforce a maximum so a caller cannot request the entire file).
2. Management-token gated.
3. Empty/missing log file → 200 with an empty list. A fresh install has no
   audit log and that is not an error.
4. Add the panel to `/console`, with the graceful-degradation behaviour above.

## Acceptance criteria

- [ ] `GET /api/audit` returns recent entries, newest first, respecting `limit`.
- [ ] `limit` is capped; an absurd value does not read the whole file into memory.
- [ ] Requires the **management** token; the read token alone is refused.
- [ ] Missing audit file → 200 with `[]`.
- [ ] `/console` shows a clear "requires management token" state rather than a broken panel.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k audit -q
```

## Log

_(record the real result before marking `[x]`)_
