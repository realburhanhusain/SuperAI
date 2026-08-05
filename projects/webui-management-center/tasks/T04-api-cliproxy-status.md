# T04 — `GET /api/cliproxy/status`

| | |
|---|---|
| **Wave** | W1 |
| **Status** | `[ ]` |
| **Depends on** | T01 |
| **Estimate** | 45 min |
| **Owner** | — |

## Goal

Report whether a CLIProxyAPI instance is reachable, so `/console` can show
proxy up/down without the user running `curl` by hand.

## Context

- `superai smoke-preflight` **already** reports whether a proxy is up at
  `127.0.0.1:8317` — see `docs/CLIPROXY_TRANSPORT.md`. **Find that existing
  check and reuse it.** Do not reimplement reachability logic; two
  implementations will drift and then disagree, and the resulting "which one is
  right?" is a worse problem than the one being solved.
- Default endpoint is `http://127.0.0.1:8317/v1` (`docs/CLIPROXY_TRANSPORT.md`).
  Resolve the configured base URL from the provider entry in
  `core/provider_catalog.py` (`OPENAI_COMPAT_PROVIDERS`, the `cliproxy` row)
  rather than hardcoding it.
- **A down proxy is the normal state, not a failure.** Nothing routes to
  cliproxy until the user merges `config/models.cliproxy.example.json` into the
  registry. `reachable: false` is a perfectly healthy response and must never
  produce a non-200 or a scary log line.

## Steps

1. Locate the reachability check used by `smoke-preflight` and factor it into a
   shared helper if it is not already callable.
2. Add `@app.get("/api/cliproxy/status")` returning at minimum:
   `{configured_base_url, reachable, models_count?}`.
3. **Set a short timeout** (~2s). This endpoint is called by a page load; a
   hanging TCP connect to a dead host must not hang `/console`.
4. Never include any API key or management key in the response — the
   configured base URL only.
5. Tests must **not** require a running proxy. Block sockets or inject a fake
   transport. See `tests/` for the precedent: an existing cliproxy test proves
   its offline claim by blocking sockets (commit `1b063c2`, "test(cliproxy):
   prove the offline claim by blocking sockets") — copy that approach.

## Acceptance criteria

- [ ] Proxy down → HTTP 200, `reachable: false`, no traceback, response within the timeout.
- [ ] Proxy up → `reachable: true` (may be verified manually; note it in the Log if so).
- [ ] Base URL is read from the provider catalog, not hardcoded in `web_app.py`.
- [ ] No secret appears in the response.
- [ ] Test suite passes with **no** proxy running and with sockets blocked.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k cliproxy -q
```

## Log

_(record the real result here before marking `[x]`)_
