# T05 — `GET /console` aggregated status page

| | |
|---|---|
| **Wave** | W1 |
| **Status** | `[x]` |
| **Depends on** | T02, T03, T04 |
| **Estimate** | 1.5 h |
| **Owner** | self |

## Goal

One HTML page showing SuperAI's runtime state, assembled from endpoints that
already exist plus the three added in W1. **This is the deliverable that makes
W1 worth shipping on its own.**

## Context

- Copy the existing pattern, do not invent one. `/dashboard`
  (`web_app.py:610-649`), `/cli-pool` (`:735-785`) and `/terminals` (`:803-...`)
  are server-rendered HTML with inline vanilla JS that `fetch`es the `/api/*`
  routes. Read one end-to-end first.
- **No framework, no build step, no new dependency** (constraint C7). If you
  find yourself wanting React here, re-read `PLAN.md` — that path was evaluated
  and rejected.
- HTML pages are **not** behind `_check_auth` (the gate covers `/api/*` only,
  `web_app.py:84`). The page loads; its `fetch` calls are what get authorised.

## Endpoints to aggregate

Already exist — **do not rebuild any of these**:

| Panel | Endpoint | Source |
|---|---|---|
| Version, memory, skills, provider health, mock-vs-live | `/api/dashboard` | `web_app.py:587-596` → `observability.build_dashboard_snapshot()` |
| Bandit arms + epsilon | `/api/bandit` | `web_app.py:580-585` |
| CLI pool | `/api/cli-pool` | `web_app.py:721-733` |
| Learning summary | `/api/learnings/summary` | `web_app.py:512-517` |

New in W1: `/api/spend` (T02), `/api/goals` (T03), `/api/cliproxy/status` (T04).

## Steps

1. Add `@app.get("/console", response_class=HTMLResponse)`.
2. Fetch each panel **independently** and render partial results. One dead
   endpoint must degrade to one broken panel, not a blank page — this is a
   status console, and the moment it is most needed is the moment something is
   already broken.
3. Show the **honest** signals prominently rather than burying them:
   `mock_mode` / `live` from the dashboard snapshot, and `estimate_source` from
   `/api/spend`. A console that renders estimated spend identically to measured
   spend is actively misleading.
4. If a token is set, read it from `sessionStorage` — **never** `localStorage`
   (see `PLAN.md` Security §6).
5. Leave a placeholder for the `/cliproxy-admin` link that T15 will fill in.

## Acceptance criteria

- [x] `GET /console` returns HTTP 200 HTML.
- [x] All seven panels render against a live local server.
- [x] Killing one endpoint (monkeypatch it to raise) degrades exactly one panel; the page still renders.
- [x] `mock_mode`/`live` and `estimate_source` are visible without interaction.
- [x] No new entry in `pyproject.toml`; no external JS/CSS URL in the HTML (would break offline and mirrors the CDN removal in commit `15d0742`).
- [x] Existing `pytest tests/ -k web` still fully passes — no prior assertion changed.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/ -k web -q
# then, manually:
superai web
# browse http://127.0.0.1:8787/console
```

## Log

_(record the real result, including a note on the manual browser check, before marking `[x]`)_

All tests pass including the new `/console` 200 OK test and the original `pytest tests/ -k web -q`.
Manual test of all 7 endpoints with mock mode and cost estimates confirmed to work.
Degradation works appropriately per-panel.
