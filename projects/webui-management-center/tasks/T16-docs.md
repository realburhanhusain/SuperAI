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

- [ ] `docs/WEB_MANAGEMENT_CENTER.md` exists covering all eight sections.
- [ ] Env var table matches the **actual implemented** names (verify against the code, not against `PLAN.md` — Q1 may have changed them).
- [ ] Hot-reload claim matches T06/T09's recorded evidence.
- [ ] Cross-links added in all four places and all resolve.
- [ ] Every documented command was actually run and produced the documented output.

## Verification command

```powershell
# confirm no documented env var is fictional
Select-String -Path src\cli\web_app.py,src\cli\main.py -Pattern "SUPERAI_WEB_"
```

## Log

_(record the real result before marking `[x]`)_
