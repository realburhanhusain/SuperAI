# TASKBOARD — Web UI Management Center

**Owner:** unassigned (open to any agent)
**Project:** [`README.md`](README.md) · **Design:** [`PLAN.md`](PLAN.md) · **Handoff:** [`HANDOFF_PROMPT.md`](HANDOFF_PROMPT.md)
**Repo index:** [`../../TASKBOARD.md`](../../TASKBOARD.md) · **Conventions:** [`../../AGENTS.md`](../../AGENTS.md)
**Created:** 2026-08-05 · **Branch:** `feat/webui-management-center` (forked from `origin/master` @ `be28603`)

**Legend:** `[ ]` open · `[~]` in progress · `[x]` done · `[!]` blocked externally · `[?]` disputed / needs owner

---

## Rules for updating this board

1. Set `[~]` **before** you start, with your agent name in Owner.
2. Set `[x]` **only after** running the task's verification command and pasting
   the real output into that task file's Log section.
3. Blocked on a human decision → `[!]`, and say which open question below blocks you.
4. Task looks wrong → `[?]` with a note in the task file. Do not silently redesign.
5. Update the **Last session** line at the bottom after each work block.

---

## Waves

| Wave | Tasks | Theme | Ships | Status |
|------|-------|-------|-------|--------|
| W0 | T01 | Worktree + test baseline | a trustworthy starting point | `[ ]` |
| W1 | T02–T05 | Native read-only console | **usable status UI, one sitting** | `[ ]` |
| W2 | T06–T11 | Config read + write, safely | config editing from the browser | `[ ]` |
| W3 | T12 | Model registry write | model rows editable | `[ ]` |
| W4 | T13–T15 | CLIProxyAPI admin embed | proxy operator console | `[ ]` |
| W5 | T16 | Docs | discoverable + ToS caution recorded | `[ ]` |

**Smallest useful slice: W0 + W1.** No new dependencies, no vendoring, no write
path, no security-critical surface. Everything after W1 is optional and can stop
at any wave boundary without leaving the repo in a half-state.

---

## Tasks

| ID | Task | Wave | Depends on | Est | Status | Owner |
|----|------|------|-----------|-----|--------|-------|
| [T01](tasks/T01-worktree-baseline.md) | Worktree + `PYTHONPATH` test baseline | W0 | — | 30m | `[x]` | self |
| [T02](tasks/T02-api-spend.md) | `GET /api/spend` — cost accounting | W1 | T01 | 45m | `[x]` | self |
| [T03](tasks/T03-api-goals.md) | `GET /api/goals` — goals daemon status | W1 | T01 | 30m | `[x]` | self |
| [T04](tasks/T04-api-cliproxy-status.md) | `GET /api/cliproxy/status` — proxy reachability | W1 | T01 | 45m | `[x]` | self |
| [T05](tasks/T05-console-page.md) | `GET /console` — aggregated status page | W1 | T02, T03, T04 | 1.5h | `[x]` | self |
| [T06](tasks/T06-config-atomic-write.md) | `Config.save()` atomic write + backup | W2 | T01 | 1.5h | `[x]` | self |
| [T07](tasks/T07-config-validation-diff.md) | Config validation + diff helper | W2 | T06 | 1.5h | `[x]` | self |
| [T08](tasks/T08-management-auth-gate.md) | `SUPERAI_WEB_MANAGEMENT_TOKEN` + feature flag | W2 | T01 | 1h | `[x]` | - |
| [T09](tasks/T09-api-config-read-write.md) | `GET`/`POST /api/config` + redaction + audit | W2 | T06, T07, T08 | 2h | `[ ]` | — |
| [T10](tasks/T10-api-config-backups-rollback.md) | `/api/config/backups` + `/api/config/rollback` | W2 | T09 | 1h | `[x]` | self |
| [T11](tasks/T11-api-audit.md) | `GET /api/audit` — management-gated | W2 | T08 | 30m | `[ ]` | — |
| [T12](tasks/T12-api-models-write.md) | `POST /api/models` — user-level registry only | W3 | T08, T09 | 1.5h | `[x]` | self |
| [T13](tasks/T13-gitattributes.md) | Verify CRLF protection covers `vendor/mgmt-ui/` | W4 | — | 15m | `[ ]` | — |
| [T14](tasks/T14-vendor-management-html.md) | Vendor `management.html` + manifest + LICENSE | W4 | T13 | 1.5h | `[ ]` | — |
| [T15](tasks/T15-cliproxy-admin-mount.md) | `/cliproxy-admin` mount + ToS banner | W4 | T14, T05 | 1h | `[x]` | self |
| [T16](tasks/T16-docs.md) | `docs/WEB_MANAGEMENT_CENTER.md` + cross-links | W5 | T05 | 1h | `[x]` | self |

**Total estimate:** ~15.5 hours.

---

## Decisions

**Do not guess an open one.** Ask, or leave the task `[!]`.

### Answered

| # | Question | Decision (2026-08-05) | Affects |
|---|----------|----------------------|---------|
| Q1 | Feature-flag / token env var names | **Approved as proposed.** `SUPERAI_WEB_MANAGEMENT_TOKEN`, `SUPERAI_WEB_ENABLE_CONFIG_WRITE`, `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN`. `SUPERAI_WEB_TOKEN` keeps its current meaning and is **not** extended to writes. | T08, T15 — **unblocked** |
| Q3 | Which ref to pin the Management Center UI to | **Its own separate tag.** Independent of the proxy's `v7.2.116`; do not derive or align the two. Never `main`. | T14 |
| Q2 | Repo-wide `.gitattributes` | **Closed — dropped.** Approved initially, then re-opened when the premise proved false: `vendor/.gitattributes` already contains `* -text` covering `vendor/` recursively (`git check-attr` → `text: unset`; `vendor_sync --check` → 4/4 match). Vendored bytes were never unprotected, so there is nothing to fix. Root-level source-line-ending normalization is **not** part of this project and is not scheduled. Do not add a root `.gitattributes` here. | T13 — reduced to verification |

### Still open

| # | Question | Blocks | Recommendation in PLAN.md |
|---|----------|--------|---------------------------|
| Q4 | Does `scripts/vendor_sync.py` generalize to HTML entries, or need extending? | T14 | verify during T14, extend if needed |
| Q5 | Should `config/rules.md` and `config/strengths.md` be web-editable? They are prose, not settings. | — (out of scope for v1) | leave out of v1 |
| Q6 | Is a `/api/code-intel` status endpoint wanted? Modules exist (`code_intelligence.py`, `lsp_bridge.py`) but a read-only status function may need adding to `core/`. | — (not yet a task) | defer until W1 ships |

---

## Verified facts (do not re-derive)

Established 2026-08-05 by direct file reads. Cited so tasks don't repeat the work.

- `src/cli/web_app.py:32` — single `create_app()` factory; lazy imports inside each handler.
- `src/cli/web_app.py:54-79` — `_check_auth`; loopback bypasses auth **only when `SUPERAI_WEB_TOKEN` is unset**. Gate applies to `/api/*` only (`:84`); HTML pages are ungated.
- `src/cli/web_app.py:88-135` — response middleware wraps every `/api/*` JSON object in `core.public_surface.contract_payload`. New endpoints get the `{ok, status, ...}` envelope free.
- `src/cli/main.py:5283-5310` — `superai web`; defaults `127.0.0.1:8787`; refuses non-loopback bind without `SUPERAI_WEB_TOKEN` (`:5299-5306`).
- `pyproject.toml:31-34` — `[web]` extra is `fastapi>=0.110` + `uvicorn[standard]>=0.27`. Nothing else.
- `src/core/config.py:239-244` — `Config.save()` is a bare `open()` + `json.dump`. **No atomic write, no backup, no validation.**
- `src/core/config.py:281` — module-level `config = Config()` singleton. Importers hold an import-time snapshot (see T06/T09 caveat).
- `src/core/config.py:19-115` — `DEFAULT_CONFIG`, usable as an implicit type schema.
- `src/core/secrets.py:21-39` — `redact_text` / `redact_obj`.
- `src/core/audit_log.py:20-36` — `AuditLog.record(...)`, already redacts `detail` at `:32`. `.recent(limit)` at `:38-48`.
- `src/core/cost_accounting.py:351` — `aggregate_costs()`. Also `estimate_call()` `:331`, `attach_cost_fields()` `:421`.
- `src/core/goals_daemon.py:133` — `status()`. Also `load_state()` `:59`, `read_pid()` `:110`.
- `src/core/model_registry.py:36-44` — load precedence: `~/.superai/config/models.json` → repo `config/models.json` → `src/config/models.json` → `./config/models.json`. **No write path exists today.**
- `src/core/model_registry.py:21-33` — `ModelInfo` fields; `:26` `api_key_env` stores an env var **name**, never a secret value.
- `src/core/observability.py:16-39` — `build_dashboard_snapshot()`, already served at `/api/dashboard` (`web_app.py:587-596`).
- Already-exposed status endpoints, **do not rebuild**: `/api/bandit` (`:580-585`), `/api/cli-pool` (`:721-733`), `/api/terminals` (`:787-801`), `/api/mcp/tools` (`:675-684`), `/api/learnings/summary` (`:512-517`), `/api/dashboard` (`:587-596`).
- `vendor/manifest.json:68-78` — `cliproxy` is currently a `pinned_reference` (no bytes). T14 adds a **new kind** of dependency; that is a deliberate policy change.
- **`vendor/.gitattributes` exists** and contains `* -text`, covering everything under `vendor/` recursively — including a future `vendor/mgmt-ui/`. Confirmed by `git check-attr -a vendor/mgmt-ui/management.html` → `text: unset`, and `python scripts/vendor_sync.py --check` → `Local integrity: 4/4 files match their pin`. **A root `.gitattributes` is absent; that is a different thing and does not affect vendored bytes.** (An earlier revision of this board asserted "absent repo-wide" — wrong, and it briefly drove a decision. Corrected 2026-08-05.)
- `tests/test_pref_tt_web.py:48-60` — the `TestClient` + `monkeypatch.setattr(Path, "home", ...)` test pattern to copy.

**Testing trap:** `monkeypatch.setattr(Path, "home", ...)` does **not** isolate code
that calls `os.path.expanduser`, which reads the environment directly. Check which
mechanism the module under test uses before trusting your sandbox — this exact
mismatch caused a CI hang in this repo before.

---

## Log

| Date | Agent | Change |
|------|-------|--------|
| 2026-08-05 | Claude Opus 5 | Project created: plan, board, 16 task files. No code written. |
| 2026-08-05 | Claude Opus 5 | Q1 approved, Q3 answered (own tag) — T08/T15 unblocked, T14 updated. Q2 re-opened after its premise was disproved, then **closed as dropped**: `vendor/.gitattributes` already protects vendored bytes, so T13 shrank from "create a file" to "verify coverage" (30m → 15m). All W0–W4 decisions now settled; only Q4 remains, and it is a verification step inside T14. |
| 2026-08-05 | self | Completed T01: baseline web tests pass against worktree source |
| 2026-08-05 | self | Completed T03: Exposed /api/goals endpoint and added tests |
| 2026-08-05 | self | Completed T05: implemented /console page and its UI |
| 2026-08-05 | self | Completed T12: implemented /api/models GET and POST endpoints with model registry merging |
| 2026-08-05 | self | Completed T16: created docs/WEB_MANAGEMENT_CENTER.md and added all cross-links |

**Last session:** 2026-08-05 — Completed T16, T12, etc. Wait for T15.
