# T08 — Management token + feature flag

| | |
|---|---|
| **Wave** | W2 |
| **Status** | `[ ]` |
| **Depends on** | T01 |
| **Estimate** | 1 h |
| **Owner** | — |
| **Blocked by** | **Q1** — confirm env var names with the owner before implementing |

## Goal

The security spine for every write route. Build it **before** the routes exist,
so no write endpoint can ever ship ungated.

## Why the existing auth is not sufficient

`_check_auth` (`web_app.py:54-79`) treats loopback as trusted whenever
`SUPERAI_WEB_TOKEN` is unset. For read-only status that is defensible. For
`POST /api/config` it is not: **any** process on the machine can reach loopback
— another local service, a malicious browser tab. "Local" is not "authorised".

## Part 1 — Feature flag (registration-time)

- Master switch: `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` (**confirm name, Q1**).
- Check it **inside `create_app()`, at route-registration time**, so that when
  the flag is off the routes are *never registered at all*.
- This is deliberately stronger than registering-then-403ing. A route that does
  not exist cannot be reached through a bug in an auth check. It also mirrors
  the discipline of the cliproxy transport, which is inert until explicitly
  opted into rather than present-but-refusing.

## Part 2 — Management token

- `SUPERAI_WEB_MANAGEMENT_TOKEN` (**confirm name, Q1**), distinct from
  `SUPERAI_WEB_TOKEN`.
- Required **unconditionally, including on loopback**. There is no bypass. This
  mirrors the Management Center's own split between a management key and the
  proxy API keys it manages.
- Accept it via `Authorization: Bearer <token>` (and optionally a header
  mirroring the existing `X-SuperAI-Token` convention).
- **Compare with `hmac.compare_digest`**, not `==` — a plain comparison leaks
  token content through timing.
- If the flag is on but the token is unset: refuse to enable the write routes,
  and log a clear reason at startup. Failing loud beats an unauthenticated
  write surface that came up quietly.

## Part 3 — Non-loopback binding

`superai web` already refuses a non-loopback bind without `SUPERAI_WEB_TOKEN`
(`main.py:5299-5306`). Extend the same refusal: binding non-loopback **with
config-write enabled** additionally requires `SUPERAI_WEB_MANAGEMENT_TOKEN`.

## Note on CSRF — no middleware needed

Header-bearer auth is CSRF-safe by construction: a foreign page cannot attach
the `Authorization` header without already holding the token. This holds **only
while the token is never stored in a cookie.** Record that as a constraint in
the code comment, so a future session adding cookie sessions sees why it matters.

## Acceptance criteria

- [ ] Flag off (default) → `/api/config` is absent from `app.routes` entirely. Assert on the route table, not on a 404.
- [ ] Flag on, token unset → write routes not enabled; clear startup log line.
- [ ] Flag on, token set, request without token **on loopback** → refused.
- [ ] Wrong token → refused; comparison uses `hmac.compare_digest`.
- [ ] `SUPERAI_WEB_TOKEN` alone does **not** grant write access.
- [ ] Non-loopback bind + write enabled + no management token → `superai web` refuses to start.
- [ ] Default `superai web` behaviour is byte-identical to before this task.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k "auth or flag or token" -q
```

## Log

_(record the real result before marking `[x]`)_
