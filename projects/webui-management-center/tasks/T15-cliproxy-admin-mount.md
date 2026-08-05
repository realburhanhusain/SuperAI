# T15 — `/cliproxy-admin` mount + ToS banner

| | |
|---|---|
| **Wave** | W4 |
| **Status** | `[ ]` |
| **Depends on** | T14, T05 |
| **Estimate** | 1 h |
| **Owner** | — |
| **Blocked by** | **Q1** (flag name) |

## Goal

Serve the vendored Management Center UI from SuperAI's web app as an operator
console for a **separate, optional** CLIProxyAPI process.

## The architectural rule — do not proxy

SuperAI's FastAPI app is a **file host only**. The browser loads
`management.html` from SuperAI, and that page's own Axios client then talks
**directly** to whatever management URL the operator enters into it.

Do **not** add a reverse proxy from SuperAI to `/v0/management`. That would:

- require reimplementing streaming log tail through a second hop,
- put the CLIProxyAPI **management key** through SuperAI's process, where it
  would land in logs and error paths — a key SuperAI has no reason to ever see,
- and couple SuperAI's request lifecycle to a second server's uptime, so a
  hung proxy becomes a hung SuperAI.

Static bytes plus a link. That is the entire integration.

## Steps

1. Mount behind the flag `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1` (**confirm name,
   Q1**), checked at `create_app()` registration time — same discipline as T08.
   Default `superai web` must not serve these bytes at all.
2. `StaticFiles` mount at `/cliproxy-admin`, serving `vendor/mgmt-ui/`. The PWA
   mount at `web_app.py:44-47` is the pattern to copy.
3. Add the link on `/console` (T05 left a placeholder), showing proxy
   reachability from `/api/cliproxy/status` (T04) next to it, so a user sees
   *before* clicking whether there is anything to manage.
4. **ToS banner.** `docs/CLIPROXY_TRANSPORT.md` records that wrapping
   subscription access as a general-purpose API may conflict with vendor terms.
   This UI includes **OAuth flows for Codex, Anthropic, Antigravity, Kimi and
   xAI** — it makes those flows one click away and highly discoverable. A
   caution that lives only in `docs/` is a caution that a UI user will never
   read. Put a visible banner on `/console` next to the admin link, text
   summarised and linked to the doc section.
5. Make the boundary legible in the UI: label it clearly as managing the
   **CLIProxyAPI proxy**, not SuperAI. A user who edits proxy config believing
   they are editing SuperAI config is the specific confusion this whole plan was
   shaped to avoid.

## Acceptance criteria

- [ ] Flag unset → `/cliproxy-admin` is not mounted; the route is absent from `app.routes`.
- [ ] Flag set → the vendored UI loads and is byte-identical to the vendored file.
- [ ] SuperAI's backend performs **no** requests to `/v0/management` (grep the diff to confirm no proxy code was added).
- [ ] `/console` shows the link, the proxy up/down state, and the ToS banner.
- [ ] The UI is labelled as managing the proxy, not SuperAI.
- [ ] Manual smoke test against a real running CLIProxyAPI, recorded in the Log. Not automatable without the Go binary in CI — say so rather than claiming coverage.

## Verification command

```powershell
$env:PYTHONPATH = "C:\Users\burhan.husain\claude\worktrees\superai-webui-mc\src"
python -m pytest tests/test_web_management_center.py -k "admin or cliproxy" -q
# then manually: set the flag, superai web, browse /cliproxy-admin
```

## Log

_(record the automated result and the manual browser check before marking `[x]`)_
