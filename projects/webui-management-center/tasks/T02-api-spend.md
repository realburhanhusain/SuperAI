# T02 — `GET /api/spend`

| | |
|---|---|
| **Wave** | W1 |
| **Status** | `[ ]` |
| **Depends on** | T01 |
| **Estimate** | 45 min |
| **Owner** | — |

## Goal

Expose cost/spend accounting as a read-only JSON endpoint, so the `/console`
page (T05) can show what has been spent without shelling out to the CLI.

## Context

- Backing function **already exists**: `core.cost_accounting.aggregate_costs()`
  at `src/core/cost_accounting.py:351`. Read its signature and return shape
  before writing the handler — do not assume the fields below are exact.
- Related helpers if `aggregate_costs()` alone is insufficient:
  `estimate_call()` (`:331`), `attach_cost_fields()` (`:421`),
  `resolve_estimate_source()` (`:148`).
- Add the route in `src/cli/web_app.py`, following the existing lazy-import
  style — import `core.cost_accounting` *inside* the handler, not at module
  top. See `web_app.py:194-200` for the pattern.
- The response middleware at `web_app.py:88-135` wraps any `/api/*` dict in the
  `{ok, status, ...}` contract envelope automatically. **Return a plain dict.**
  Do not hand-roll the envelope.
- Auth: standard `/api/*` rule (`_check_auth`, `web_app.py:54-79`). This is a
  read endpoint — it does **not** need the management token.

## Steps

1. Read `cost_accounting.aggregate_costs()` and note its real return shape.
2. Add `@app.get("/api/spend")` to `create_app()` in `web_app.py`, placed near
   the other read endpoints (e.g. after `/api/bandit` at `:580-585`).
3. Handle the empty case: a fresh install with no spend history must return a
   valid, well-formed response — **not** a 500 and not `null`.
4. Preserve `estimate_source` fidelity. Per `docs/COST_ACCOUNTING.md` and
   `docs/CLIPROXY_TRANSPORT.md`, the distinction between `actual`, `registry`
   and `fallback` is load-bearing honesty, not decoration. If the endpoint
   flattens or drops it, the UI will present invented prices as measured ones.

## Acceptance criteria

- [ ] `GET /api/spend` returns HTTP 200 with the contract envelope `{ok: true, ...}`.
- [ ] Response includes per-model breakdown and the `estimate_source` distinction.
- [ ] With no spend history present, returns 200 with zeroed/empty values — not an error.
- [ ] No module-level import added to `web_app.py` (lazy-import pattern preserved).
- [ ] New test in `tests/test_web_management_center.py` covering both the populated and empty cases.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k spend -q
```

## Log

_(record the real result here before marking `[x]`)_
