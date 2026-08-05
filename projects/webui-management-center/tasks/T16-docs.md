# T16 — `docs/WEB_MANAGEMENT_CENTER.md` + cross-links

| | |
|---|---|
| **Wave** | W5 |
| **Status** | `[ ]` |
| **Depends on** | T05 (can be written incrementally as later waves land) |
| **Estimate** | 1 h |
| **Owner** | — |

## Goal

Make the feature discoverable and its risks legible, in the idiom this repo
already uses for exactly this kind of opt-in integration.

## Model to follow

`docs/CLIPROXY_TRANSPORT.md` is the template — the same author-audience and the
same shape of feature. Note specifically what it does well and reproduce it:

- states plainly that the feature is **additive and opt-in**, and that nothing
  was removed;
- gives a **table** of what changed and where;
- is explicit about where a number is exact and where it is estimated, rather
  than presenting both the same way;
- names a caution (vendor ToS) instead of burying it;
- explains *why* a naming choice was made (`cliproxy:` vs `cli:`), which is what
  stops a later session from "simplifying" it back into a bug.

## Required content

1. **What this is and is not.** Two surfaces: SuperAI-native config/status
   pages, and an embedded console for a *separate* proxy. Say clearly that the
   Management Center manages CLIProxyAPI, not SuperAI — this is the single most
   likely misunderstanding.
2. **Enabling it.** Env var table: `SUPERAI_WEB_TOKEN`,
   `SUPERAI_WEB_MANAGEMENT_TOKEN`, `SUPERAI_WEB_ENABLE_CONFIG_WRITE`,
   `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN` — what each does, what is required for
   what, and the default (everything off).
3. **Endpoint reference.** Read vs write, and which token each needs.
4. **Config-write semantics.** Atomic write, backup location and retention,
   validation, diff preview, rollback, and the `~/.superai/` precedence rule
   (writes never touch repo-tracked files).
5. **Hot reload — state the truth from T06/T09.** If some settings need a
   restart because of the `config.py:281` singleton, say **which**. Do not write
   "applies immediately" unless it was demonstrated.
6. **Security.** The separate management token and why loopback is not trusted
   for writes; `sessionStorage` not `localStorage`; the CSRF-safe-by-construction
   property **and its precondition** (never move the token into a cookie);
   audit logging.
7. **ToS caution**, repeated from `docs/CLIPROXY_TRANSPORT.md` rather than
   merely linked — it is sharper here because the UI exposes OAuth flows.
8. **Vendoring.** What is pinned, to which ref, and how to update it (including
   that `.gitattributes` must stay ahead of the bytes).

## Cross-links

- `docs/CLIPROXY_TRANSPORT.md` → link to the new doc.
- `docs/README.md` (docs map) → add the entry.
- Root `TASKBOARD.md` → the project row added at scaffold time; update its status.
- `projects/webui-management-center/TASKBOARD.md` → final status and Log entry.

## Acceptance criteria

- [x] `docs/WEB_MANAGEMENT_CENTER.md` exists covering all eight sections.
- [x] Env var table matches the **actual implemented** names (verify against the code, not against `PLAN.md` — Q1 may have changed them).
- [x] Hot-reload claim matches T06/T09's recorded evidence.
- [x] Cross-links added in all four places and all resolve.
- [x] Every documented command was actually run and produced the documented output.

## Verification command

```powershell
# confirm no documented env var is fictional
Select-String -Path src\cli\web_app.py,src\cli\main.py -Pattern "SUPERAI_WEB_"
```

## Log

```
src\cli\web_app.py:39:    enable_config_write = os.getenv("SUPERAI_WEB_ENABLE_CONFIG_WRITE") == "1"
src\cli\web_app.py:40:    management_token = (os.getenv("SUPERAI_WEB_MANAGEMENT_TOKEN") or "").strip()
src\cli\web_app.py:60:        - SUPERAI_WEB_TOKEN required for non-loopback API access
src\cli\web_app.py:64:        token = (os.getenv("SUPERAI_WEB_TOKEN") or "").strip()
src\cli\web_app.py:66:        # Allow loopback without token only when SUPERAI_WEB_TOKEN unset
src\cli\web_app.py:72:                detail="SUPERAI_WEB_TOKEN required for non-loopback API access",
src\cli\web_app.py:166:            logging.getLogger("superai.web_app").error("SUPERAI_WEB_ENABLE_CONFIG_WRITE is on but SUPERAI_WEB_MANAGEMENT_TOKEN is unset. Write 
routes will NOT be enabled.")
src\cli\web_app.py:946:        Auth: SUPERAI_WEB_TOKEN if set (Bearer / x-superai-token).
src\cli\web_app.py:1177:const token = sessionStorage.getItem('SUPERAI_WEB_TOKEN') || sessionStorage.getItem('SUPERAI_WEB_MANAGEMENT_TOKEN');
src\cli\main.py:5301:    if not loopback and not (os.getenv("SUPERAI_WEB_TOKEN") or "").strip():
src\cli\main.py:5303:            "[red]Refusing to bind non-loopback without SUPERAI_WEB_TOKEN.[/red]\n"
src\cli\main.py:5304:            "Set SUPERAI_WEB_TOKEN or use --host 127.0.0.1"
src\cli\main.py:5308:    enable_config_write = os.getenv("SUPERAI_WEB_ENABLE_CONFIG_WRITE") == "1"
src\cli\main.py:5309:    management_token = (os.getenv("SUPERAI_WEB_MANAGEMENT_TOKEN") or "").strip()
src\cli\main.py:5312:            "[red]Refusing to bind non-loopback with SUPERAI_WEB_ENABLE_CONFIG_WRITE enabled without SUPERAI_WEB_MANAGEMENT_TOKEN.[/red]\n"
src\cli\main.py:5313:            "Set SUPERAI_WEB_MANAGEMENT_TOKEN or disable write routes."
src\cli\main.py:5317:    if (os.getenv("SUPERAI_WEB_TOKEN") or "").strip():
src\cli\main.py:5318:        console.print("[dim]API auth enabled (SUPERAI_WEB_TOKEN)[/dim]")
```
