# T03 — `GET /api/goals`

| | |
|---|---|
| **Wave** | W1 |
| **Status** | `[ ]` |
| **Depends on** | T01 |
| **Estimate** | 30 min |
| **Owner** | — |

## Goal

Expose the goals daemon's status as a read-only JSON endpoint for the `/console`
page.

## Context

- Backing function **already exists**: `core.goals_daemon.status()` at
  `src/core/goals_daemon.py:133`. This is pure wiring — no new logic in
  `core/`.
- Supporting reads if needed: `load_state()` (`:59`), `read_pid()` (`:110`),
  `_pid_alive()` (`:89`).
- **Read-only means read-only.** `goals_daemon` also exposes `tick()` (`:175`),
  `run_loop()` (`:279`), `start_background()` (`:354`) and `stop()` (`:457`).
  This endpoint must call **none** of them. A status endpoint that starts a
  daemon as a side effect is a bug, and an HTTP GET that mutates state is worse.
- Lazy-import inside the handler, plain dict return, standard `/api/*` auth —
  same as T02.

## Steps

1. Read `status()` and note its real return shape.
2. Add `@app.get("/api/goals")` to `create_app()` in `web_app.py`.
3. Handle the daemon-not-running case cleanly: return 200 with
   `running: false`, not a 404 or a 500. "Not running" is the normal state on a
   fresh install, exactly as a down CLIProxyAPI is (see `docs/CLIPROXY_TRANSPORT.md`).
4. If `status()` reports a stale PID file, surface that honestly rather than
   reporting `running: true` on the strength of a file that outlived its process.

## Acceptance criteria

- [ ] `GET /api/goals` returns HTTP 200 with the contract envelope.
- [ ] Daemon stopped → 200 with `running: false`. No exception, no 404.
- [ ] The handler calls no mutating function from `goals_daemon`.
- [ ] Test covers both the running and not-running cases (fake the state file; do not actually spawn a daemon in tests).

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k goals -q
```

## Log

_(record the real result here before marking `[x]`)_
