# SuperAI ⇄ CLI Proxy API Management Center — Integration Plan

> Drafted by Fable 5 (planning role, read-only) on 2026-08-05, against
> `C:\Users\burhan.husain\Documents\Personal\github\SuperAI`.
> Open questions 1–4 were resolved after drafting by direct verification — see
> **"Resolved after drafting"** at the end, which supersedes the corresponding
> rows in the Open Questions list.
>
> **Status: proposal. Nothing has been implemented. No SuperAI file was modified.**

## Executive Summary

**Recommendation: Option (D), Hybrid — but sequenced so the useful part ships first without any fork.**

Concretely, two independent workstreams, only the first of which is required to satisfy "runtime status monitoring" and most of "simplify configuration":

1. **Extend `src/cli/web_app.py`** (already exists, already FastAPI, already has an auth model) with a small set of new **read** endpoints (bandit, cli-pool, cost/spend, learning engine, goals daemon, MCP tools — most already have a backing module) and a handful of new **write** endpoints for the config surfaces that are genuinely SuperAI's (`config.json` via `core.config.Config`, `config/models.json` via `core.model_registry`). This is Option (E) from the brief, done properly instead of dismissed — it costs nothing new (no Bun, no fork, no vendor entry) and directly serves "SuperAI configuration modifications and runtime status monitoring."
2. **Vendor the Management Center's prebuilt `management.html` unmodified** (pin by exact upstream commit under `vendor/`, per `vendor/README.md`'s existing pattern) and serve it read-only at `/cliproxy-admin` from the same FastAPI app, purely as an operator console for the **separate, optional CLIProxyAPI process** SuperAI may be talking to over `cliproxy:*` model routes. This is Option (A), scoped honestly: it manages the proxy, not SuperAI.

Both land under one process (`superai web`), on one port, as one HTML shell with two panes — hence "hybrid" — but **nothing is forked, adapted, or rebuilt**. Option (B) (fork the TypeScript UI and repoint its Axios layer at a new SuperAI backend) is rejected: it would require standing up a Bun/Vite/React toolchain inside a Python repo, maintaining a fork of a fast-moving external project, and reimplementing a `/v0/management`-shaped API purely to satisfy a client that already speaks plain fetch/JSON just as well from a five-line vanilla-JS page — SuperAI's existing `/dashboard`, `/cli-pool`, `/palace` pages already prove this pattern out at zero framework cost (`src/cli/web_app.py:610-649`, `:735-785`). Option (C) (backend shim so the unmodified UI drives SuperAI) is rejected for the same reason plus a worse one: SuperAI's config model (flat `config.json` + JSON model registry + markdown `rules.md`/`strengths.md` + plugin registry) has no faithful mapping to CLIProxyAPI's YAML `config.yaml` schema that the MC UI's editor, diff view, and validation logic are hard-coded against — building that shim would mean lying to the UI about what it's editing.

**Why not "manufacture work to justify adopting the repo":** the brief's own framing is correct — the MC UI is written *against* `/v0/management` on the Go proxy. It has zero knowledge of SuperAI's bandit router, cost accounting, learning engine, MCP tools, or goals daemon, and no amount of respectful reuse changes that its React state, CodeMirror YAML schema, and OAuth flows are proxy-shaped. Reusing its *patterns* (YAML diff preview, log tail, config validation before write) is worth doing in the new SuperAI-native endpoints; reusing its *code* is not, because the object it edits is wrong.

**Smallest useful first slice (ships in one sitting):** Phase 1 below — three new read-only GET endpoints added to the existing `web_app.py`, wired into one new `/console` HTML page, zero new dependencies, zero vendor changes, opt-in via existing `SUPERAI_WEB_TOKEN` gate.

---

## Verified Current-State Findings

All claims below are cited `file:line` and were read directly, not inferred.

### The existing web app
- `src/cli/web_app.py` is a single `create_app()` factory (`web_app.py:32`), 891 lines, imports lazily inside each route handler (consistent pattern throughout — e.g. `web_app.py:194-200`).
- Auth: `_check_auth` (`web_app.py:54-79`) — loopback clients (`127.0.0.1`/`::1`/`localhost`/`testclient`, `web_app.py:52`) bypass auth **only if `SUPERAI_WEB_TOKEN` is unset**; any non-loopback request or any request once the token is set requires `Authorization: Bearer <token>` or `X-SuperAI-Token`. Applied via `@app.middleware("http")` gate on `/api/*` only (`web_app.py:84`) — HTML pages themselves are unauthenticated even when the token is set, they just can't successfully call `/api/*` from the browser without it baked into JS (a design point returned to in Security).
- A second middleware (`web_app.py:88-135`) wraps every `/api/*` JSON object response in `core.public_surface.contract_payload` — any new endpoint automatically gets `{ok, status, ...}` shape for free, no per-handler code needed.
- CLI entrypoint: `superai web --host --port` (`src/cli/main.py:5283-5310`). Defaults `127.0.0.1:8787`. Refuses non-loopback bind without `SUPERAI_WEB_TOKEN` set (`main.py:5299-5306`) — this is the existing "opt-in for remote" discipline the new work must mirror.
- Dependency gate: `[web]` extra = `fastapi>=0.110`, `uvicorn[standard]>=0.27` only (`pyproject.toml:31-34`). No frontend build tooling anywhere in the repo today.
- 31 routes total. Notably `/api/dashboard` (`web_app.py:587-596`) already calls `core.observability.build_dashboard_snapshot()`, which already aggregates: version, task history (`observability.py:41-58`), memory stats, skills, CLIs, `bandit_arms` count, preferences, `plugins_enabled`, `provider_health`, `recent_logs`, `messengers`, and `mock_mode`/`honesty`/`live` flags (`observability.py:16-39`). This is a large fraction of "runtime status monitoring" already built — a new console page can mostly just render this existing endpoint plus 2–3 more targeted ones.
- `/api/bandit` (`web_app.py:580-585`) already exposes `core.bandit_router.EpsilonGreedyBandit` state (epsilon, arms, path) — **exists, read-only, done**.
- `/api/cli-pool` and `/api/terminals` (`web_app.py:721-733`, `:787-801`) already expose `core.cli_pool.ParallelCLIManager` and `core.terminal_pool.ParallelTerminalManager` snapshots — **exists, read-only, done**.
- `/api/mcp/tools` (`web_app.py:675-684`) already exposes MCP tool list — **exists, read-only, done**.
- **Not currently exposed via web**: spend/cost accounting (`core.cost_accounting`), goals daemon (`core.goals_daemon`), and — critically — **any config write path**. There is exactly one existing write endpoint touching config-like state: `POST /api/preferences` (`web_app.py:395-401`), which writes through `core.preferences.UserPreferenceModel`, not `core.config.Config`. No endpoint today reads or writes `~/.superai/config.json`, `config/models.json`, `config/rules.md`, or `config/strengths.md`. This confirms the brief's framing: SuperAI's web surface today is read-mostly, and a config-write UI is new attack surface, not an extension of an existing one.

### Config surfaces
- `src/core/config.py`: `Config` class, JSON-backed (`config.py:16-122`). Load order: built-in `DEFAULT_CONFIG` (`config.py:19-115`) → `~/.superai/config.json` (`config.py:152-161`) → project-local `./.superai/config.json` (`config.py:218-229`) → `SUPERAI_*` env overrides (`config.py:163-206`, env always wins last). `.get`/`.set`/`.save` are trivial dict ops (`config.py:231-244`) — no schema validation, **no atomic write** (plain `open(...).write` then `json.dump`, `config.py:239-244` — a crash mid-write truncates the file, no temp-file-then-rename), no versioning, no diff. **This is a real gap the plan must close for any write endpoint.**
- `src/core/secrets.py`: `redact_text`/`redact_obj` (`secrets.py:21-39`) pattern-match `api[_-]?key|token|secret|password`, `sk-...`, `Bearer ...`, Slack/GitHub/AWS key shapes, and replace with `***REDACTED***`. Already used by `AuditLog.record` (`audit_log.py:32`). **This must be applied to every config-editor GET response** — SuperAI's config doesn't centrally store provider API keys (those are read from env vars per `provider_catalog.py`), so the redaction surface is smaller than CLIProxyAPI's `config.yaml` (which stores keys inline) — a genuine simplification in SuperAI's favour, but still worth asserting with a test.
- `src/core/model_registry.py`: `ModelRegistry` (`model_registry.py:53-`) loads from, in precedence order (`model_registry.py:36-44`): `~/.superai/config/models.json` → repo `config/models.json` → `src/config/models.json` → `./config/models.json`. No write path exists in this module today (read-only registry).
- `src/core/audit_log.py`: `AuditLog.record(action, detail, actor, outcome)` (`audit_log.py:20-36`) appends JSON lines to `~/.superai/audit.jsonl`, redacting `detail` through `secrets.redact_obj` before writing (`audit_log.py:32`). `AuditLog.recent(limit)` reads it back (`audit_log.py:38-48`). **This already exists and is exactly the mechanism constraint 4 asks about** — every config-write endpoint must call `AuditLog().record(...)` with `actor="web"`.
- `vendor/README.md` and `vendor/manifest.json` confirm the vendoring policy: `vendored_files` (bytes committed, pinned by commit/npm version + sha256, `vendor/README.md:12-24`) vs `pinned_reference` (no bytes, doc-only citation, `vendor/README.md:15-16`). Current entries: `cliproxy-models` (vendored_files, commit `fb13a81...`), `vega` (vendored_files, npm, major-line pinned), `cliproxy` itself (**pinned_reference only** — `manifest.json:68-78`, "SuperAI speaks its OpenAI-compatible protocol over HTTP and reads none of its source, so nothing is vendored"). **This is load-bearing precedent**: today's policy is explicitly "we don't vendor CLIProxyAPI's bytes because we don't read them." Vendoring `management.html` bytes is a *new kind* of dependency on that project and must be added as a new `vendored_files` entry — a deliberate, visible policy change, not a drive-by edit.
- `.gitattributes` **does not exist in this repo** (verified). Constraint 2's "must land before vendored bytes, never the same commit" therefore requires **creating** the file, not editing one, and the two-commit sequencing applies from a clean slate.
- `docs/CLIPROXY_TRANSPORT.md` fully read. Confirms: pin is `v7.2.116` / commit `a88197f8...` (`manifest.json:72-73`); the ToS caution is explicit and must be repeated for any UI surfacing OAuth flows; provider is inert until models are merged into the registry; default endpoint `http://127.0.0.1:8317/v1`; `superai smoke-preflight` already reports proxy up/down.

### Concurrency / worktree state
- `git status --branch` on `master` shows `ahead 22` of `origin/master` with an untracked `update_models.py` at repo root — confirms the brief's warning: **local `master` is not trustworthy as a base**; any new branch must fork from `origin/master`.

---

## Options Analysis

| Option | Meets "simplify SuperAI config" | Meets "runtime monitoring" | New toolchain? | Fork maintenance burden | Attack surface added | Verdict |
|---|---|---|---|---|---|---|
| (A) Embed MC as-is for proxy only | No (manages proxy, not SuperAI) | Partial (proxy-only) | No | None (pinned bytes) | Low–medium (adds an admin console with OAuth flows) | **Adopt, scoped to proxy pane only** |
| (B) Fork/adapt the TS UI, repoint at new SuperAI backend | Yes | Yes | Yes (Bun/Vite/React in a Python repo) | High — track upstream security fixes and layout changes forever | Medium | Rejected — cost disproportionate to five existing vanilla-JS pages already doing this job |
| (C) `/v0/management`-shaped shim in SuperAI, unmodified UI | Partially, dishonestly | Yes (for the proxy pane) | No | Low (shim, not fork) | High — UI would present SuperAI config through a schema (CLIProxyAPI's) it was never designed to hold, inviting silent data loss on fields that don't map | Rejected — lossy/dishonest mapping |
| (D) Hybrid: (A) + native pages in existing `web_app.py` | Yes (native pages) | Yes (native pages + existing endpoints) | No | Low (only the vendored HTML, no build) | Managed explicitly (see Security) | **Chosen** |
| (E) Extend `web_app.py` only, skip MC UI entirely | Yes | Yes | No | None | Lowest | Subsumed into (D) as the majority of the work; (A) added on top costs one vendor entry and ~20 lines of routing |

**Why (D) over pure (E):** the user explicitly named this repo, and status of a running CLIProxyAPI backend (auth files, quota, per-vendor OAuth state) genuinely is runtime status SuperAI's own modules cannot see — SuperAI only knows "is `127.0.0.1:8317` reachable" via `smoke-preflight`; it doesn't know per-vendor OAuth expiry, quota remaining, or auth file state. The MC UI does. Embedding it costs one `vendored_files` manifest row and no code. Not embedding it leaves CLIProxyAPI status a manual `curl` exercise when the tool to avoid that already exists MIT-licensed. Embedding it as a **read-mostly operator console for a genuinely separate server**, rather than pretending it edits SuperAI, keeps the honesty property.

---

## Target Architecture

```
                         Browser
                            │
                            │  HTTP (loopback by default)
                            ▼
        ┌───────────────────────────────────────────┐
        │  superai web  (uvicorn, FastAPI, :8787)    │
        │  src/cli/web_app.py :: create_app()        │
        │                                            │
        │  ┌─────────────┐   ┌─────────────────────┐ │
        │  │ Existing    │   │ NEW: /console       │ │
        │  │ /api/* read │   │  SuperAI-native page│ │
        │  │ endpoints   │   │  + write endpoints  │ │
        │  │ (unchanged) │   │  under /api/config/*│ │
        │  └──────┬──────┘   └──────────┬──────────┘ │
        │         │                     │            │
        │         ▼                     ▼            │
        │  observability.py,      config.py,         │
        │  bandit_router.py,      model_registry.py, │
        │  cli_pool.py, mcp_*     audit_log.py,      │
        │                         secrets.py         │
        │                                            │
        │  ┌────────────────────────────────────────┐│
        │  │ NEW: /cliproxy-admin                   ││
        │  │  StaticFiles mount → vendored,         ││
        │  │  unmodified management.html            ││
        │  │  Browser talks DIRECTLY to the proxy's ││
        │  │  /v0/management — NOT proxied through  ││
        │  │  SuperAI's FastAPI app.                ││
        │  └───────────────────┬────────────────────┘│
        └──────────────────────┼─────────────────────┘
                               │  browser → proxy, direct
                               │  (Bearer <MANAGEMENT_KEY>,
                               │   entered client-side)
                               ▼
                 ┌──────────────────────────────┐
                 │ CLIProxyAPI (Go binary/Docker)│
                 │ :8317 — separate process,     │
                 │ separately started/stopped,   │
                 │ optional, unrelated lifecycle │
                 │ /v0/management, /v1/chat/*    │
                 └──────────────────────────────┘
```

**Key architectural decision: `/cliproxy-admin` does not proxy through SuperAI's backend.** The vendored `management.html` is served as static bytes and its bundled Axios client talks straight from the browser to whatever management URL the operator configures inside that UI (same as running it standalone). SuperAI's FastAPI app is only the **file host**, not a network intermediary. This avoids (a) building a reverse-proxy with streaming log support, (b) SuperAI ever seeing or storing the CLIProxyAPI management key, and (c) coupling SuperAI's request lifecycle to a second server's uptime. The only integration points are a link on `/console` and one `GET /api/cliproxy/status` health check.

---

## API Surface Specification

All new routes live in `src/cli/web_app.py`, follow the existing lazy-import-inside-handler style, and pass through the existing contract middleware unchanged.

### Read (status) — additive, low risk

| Method | Path | Backing module | Auth | Response shape (sketch) |
|---|---|---|---|---|
| GET | `/api/spend` | `core.cost_accounting.aggregate_costs()` (`cost_accounting.py:351`) | same as `/api/*` today | `{daily_spent_usd, daily_budget_usd, run_budget_usd, by_model: {...}, estimate_source_breakdown: {...}}` |
| GET | `/api/goals` | `core.goals_daemon.status()` (`goals_daemon.py:133`) | same | `{running, pid, active_goals, last_tick}` |
| GET | `/api/learning` | `core.learning_engine.LearningEngine` (already partly exposed at `/api/learnings/summary`, `web_app.py:512-517`) | same | extend existing response rather than duplicate |
| GET | `/api/audit` | `core.audit_log.AuditLog.recent(limit)` | **management token** (see Security §8) | `{entries: [...]}`, already redacted at write time (`audit_log.py:32`) |
| GET | `/api/cliproxy/status` | thin wrapper reusing `smoke-preflight`'s existing reachability check — locate and reuse, do not reimplement | same | `{configured_base_url, reachable, models_count?}` |
| GET | `/api/code-intel` | `core.code_intelligence` / `core.lsp_bridge` | same | LSP/toolchain availability snapshot — confirm a read-only status function exists before wiring |
| GET | `/console` | new HTML page (vanilla JS + fetch, matching `/dashboard` at `web_app.py:610-649`) | page unauthenticated (matches existing pattern); its fetches carry the token if set | renders the above plus a link to `/cliproxy-admin` |

### Write (config) — new, security-critical

| Method | Path | Backing module | Auth | Semantics |
|---|---|---|---|---|
| GET | `/api/config` | `core.config.Config().show()` (`config.py:246-247`) | **management token, unconditionally, even on loopback** | Full config dict, run through `secrets.redact_obj` before serializing |
| POST | `/api/config` | new; validates then `Config().set()` / a new `Config.update_many()` | same | Body `{changes: {key: value}}`. Records `AuditLog().record("config.write", ..., actor="web")` |
| GET | `/api/config/diff` | new | same | Proposed changes → unified diff of `config.json` before/after. **Does not write.** |
| GET | `/api/models` | `core.model_registry.ModelRegistry` | same | Registry rows carry `api_key_env` — an env var *name*, never a value (`model_registry.py:26`). Structural advantage over CLIProxyAPI's inline-key `config.yaml`. |
| POST | `/api/models` | new — writes to `~/.superai/config/models.json` **only**, never the repo copy | same | Validates against `ModelInfo` fields (`model_registry.py:21-33`); backup-then-write |
| GET | `/api/config/backups` | new | same | Lists snapshots for rollback |
| POST | `/api/config/rollback` | new | same | Restores a named snapshot, audit-logged |

**Open question for Burhan:** `config/rules.md` and `config/strengths.md` are markdown prose, not structured config. Recommendation: leave out of v1 web editing — a text-area editor adds surface area without matching the "simplify configuration" ask, which reads as being about `config.json`/model-registry knobs.

---

## Config-Write Semantics

Current state has none of this — `Config.save()` is a bare `open()` + `json.dump` (`config.py:239-244`), no backup, no atomicity, no diff. Required additions in `core/config.py` (and a small sibling for `models.json`, since `model_registry.py` has no write path today):

1. **Atomic write** — write `config.json.tmp` in the same directory, `fsync`, then `os.replace()`. Prevents truncation on crash mid-write, a real gap today.
2. **Backup before write** — copy current file to `~/.superai/backups/config-<timestamp>.json`. The `backups/` dir already exists in `Config.initialize()`'s layout (`config.py:137`), currently unused for this purpose.
3. **Validation before write** — reject unknown keys unless explicitly allowed (typo protection), type-check against `DEFAULT_CONFIG`'s value types (`config.py:19-115`) as an implicit schema, bound-check numeric fields (`bandit_epsilon` 0–1, `budget_daily_usd` ≥ 0; enumerate exact bounds during implementation, not guessed here).
4. **Diff preview** (mirrors MC's own diff-preview UX) — `GET /api/config/diff` returns the diff without writing; UI shows it before the user confirms the POST.
5. **Rollback** — `POST /api/config/rollback {backup_id}`, itself audit-logged.
6. **Hot-reload vs restart** — `config.py:281` defines a module-level `config = Config()` singleton. Any long-running process that imports *that* object holds a snapshot taken at import time and will not see a web-issued write until restart. **Enumerate the importers of the singleton before claiming hot-reload works**; where a stale read matters, either construct a fresh `Config()` per request or add an explicit reload hook. Do not assert hot-reload in docs until this is measured.
7. **Precedence honoured, not fought** — writes always target `~/.superai/config.json` and `~/.superai/config/models.json`, never repo-tracked files.

---

## Runtime Status Monitoring — signal inventory

| Signal | Existing endpoint? | Notes |
|---|---|---|
| Bandit arms / epsilon | Yes — `/api/bandit` (`web_app.py:580-585`) | done |
| CLI pool jobs | Yes — `/api/cli-pool` (`web_app.py:721-733`) | done |
| Terminal sessions | Yes — `/api/terminals` (`web_app.py:787-801`) | done |
| Spend / cost accounting | **No** | new `/api/spend` → `cost_accounting.aggregate_costs()` (`cost_accounting.py:351`) |
| Learning engine summary | Yes — `/api/learnings/summary` (`web_app.py:512-517`) | done; fold into `/console` |
| Daemon / goals | **No** | new `/api/goals` → `goals_daemon.status()` (`goals_daemon.py:133`) |
| MCP tools | Yes — `/api/mcp/tools` (`web_app.py:675-684`) | done |
| LSP / code-intelligence | **No** | modules exist (`code_intelligence.py`, `code_intelligence_advanced.py`, `lsp_bridge.py`); confirm a read-only status function before promising the endpoint |
| Dashboard aggregate (version, history, memory, skills, provider_health, mock/live) | Yes — `/api/dashboard` (`web_app.py:587-596`, backed by `observability.build_dashboard_snapshot`) | done — largest single existing win |
| CLIProxyAPI reachability | **No** | new `/api/cliproxy/status`, reuse `smoke-preflight`'s check |
| CLIProxyAPI detail (OAuth/quota/auth files) | **Out of scope for SuperAI's own API by design** | covered by the embedded MC UI at `/cliproxy-admin`, deliberately not duplicated |

---

## Security

1. **Auth model for write endpoints — separate management scope required.** Today's binary "loopback-is-trusted-unless-token-set" model (`web_app.py:50-79`) is defensible for read-mostly status endpoints but is **not sufficient once `POST /api/config` exists**, because any process on the same machine (a malicious browser tab, another local service) can reach loopback. Gate all `/api/config*` and `/api/models` write routes behind a **separate `SUPERAI_WEB_MANAGEMENT_TOKEN`**, required unconditionally including loopback, distinct from `SUPERAI_WEB_TOKEN` which continues to gate read/status routes under the existing rule. This mirrors the MC's own split between a management key and proxy keys.
2. **CSRF.** All new write routes are JSON POSTs read via `await request.json()` (matching `web_app.py:264`), not form posts. Today's auth is header-bearer only, which is inherently not CSRF-exploitable by a foreign page since it cannot attach the header without already holding the token. **Conclusion: the current bearer-token-only model is CSRF-safe by construction as long as the token is never stored in a cookie.** Document that as a constraint on future changes; do not add unneeded CSRF middleware now.
3. **Loopback-vs-remote binding default.** Unchanged from today (`main.py:5299-5306`). Extend the same refusal to require `SUPERAI_WEB_MANAGEMENT_TOKEN` when config-write routes are enabled and the bind is non-loopback.
4. **Secret redaction.** `core.secrets.redact_obj` (`secrets.py:30-39`) wraps every `/api/config` and `/api/models` GET response before serialization — defence in depth against a future field that stores a literal, and against a user pasting a raw key into a free-text config value. Test: a config containing an `sk-...`-shaped string must round-trip redacted through `/api/config`.
5. **Audit logging.** Every `POST /api/config`, `POST /api/models`, `POST /api/config/rollback` calls `AuditLog().record(action, detail, actor="web", outcome=...)` (`audit_log.py:20-36`), which already redacts. `GET /api/audit` surfaces this in the console. Pure wiring, no new module.
6. **Client-side token storage.** The MC UI stores its bearer token client-side. For SuperAI's own `/console`, the same is unavoidable if the page calls authenticated `/api/*` from JS — use `sessionStorage` (cleared on tab close), never `localStorage`, and never persist the management token beyond the tab session. **Residual risk, documented not solved:** an XSS in `/console`'s own JS would leak it (low likelihood — static, hand-written, no third-party JS).
7. **ToS caution, sharpened.** `docs/CLIPROXY_TRANSPORT.md` already states that wrapping subscription access as a general API may conflict with vendor ToS. Embedding the MC UI's OAuth flows makes that one click closer and more discoverable — surface the caution **in the `/console` page itself** (a visible banner linking to the doc), not only in `docs/`.
8. **`GET /api/audit` sensitivity.** Once config writes are audited, the log becomes a record of configuration history. Gate it behind the management token, not the lighter read token — it reveals write intent and timing even when redacted.

---

## Additive / Opt-in — required tests

Mirror the existing precedent (transport inert until models merged; a test asserting the default registry has zero cliproxy models — locate that exact test and imitate its structure).

- `test_web_app_default_has_no_config_write_routes` — with no env vars set, `create_app()`'s route table does not include `/api/config` as a writable route. Recommend `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` as the master switch checked **at `create_app()` time**, so the routes are never registered rather than registered-but-403ing. Strongest form of "inert unless enabled."
- `test_web_app_config_write_requires_management_token` — with the feature enabled but `SUPERAI_WEB_MANAGEMENT_TOKEN` unset, `POST /api/config` on loopback is refused, **not** silently succeeding.
- `test_cliproxy_admin_route_requires_opt_in` — `/cliproxy-admin` gated behind `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1`, so a default `superai web` does not even serve the vendored HTML.

---

## Vendoring / CI

`management.html` is a single self-contained file (`vite-plugin-singlefile` output), small enough to commit directly, matching the `vendored_files` pattern already used for `vega` (`manifest.json:29-67`). **Recommendation: commit the built artifact, do not build in CI.** It matches existing policy (`vega` is a pre-built npm artifact, not built from source here), avoids introducing Bun to CI entirely — satisfying constraint 6 outright — and MIT permits redistribution of the built artifact provided attribution is carried.

Commit order (constraint 1 is explicit about sequencing — `.gitattributes` must land in its **own earlier commit**, never the same one as the bytes):

1. **Commit 1** — create `.gitattributes` (absent today) with a rule marking `vendor/mgmt-ui/*.html` binary / `-text` so CRLF conversion never touches it.
2. **Commit 2** — add the vendored `management.html` bytes under `vendor/mgmt-ui/`, plus a new `manifest.json` entry (`kind: vendored_files`, exact upstream commit, sha256, MIT note) and a `LICENSE`/`NOTICE` file alongside for attribution.
3. **Commit 3** — `src/cli/web_app.py` changes (new routes, mount).
4. **Commit 4+** — config-write module changes, tests, docs.

All in a dedicated `git worktree` forked from `origin/master` (not local `master`, which is 22 commits ahead and untrusted).

---

## Phased Execution Plan

### Phase 0 — Setup (30 min)
- `git worktree add ../superai-mgmt-center -b feat/web-management-center origin/master`
- `$env:PYTHONPATH="<worktree>\src"` for all subsequent test runs (constraint 2), sanity-checked with `python -c "import core.config as c; print(c.__file__)"`.
- **Acceptance:** `pytest tests/ -k web` passes unmodified in the new worktree, proving isolation from the ~13 concurrent branches.

### Phase 1 — Native read-only console (smallest useful slice, one sitting)
- Add `GET /api/spend`, `GET /api/goals`, `GET /api/cliproxy/status` (all three backing functions confirmed to exist).
- Add `GET /console` aggregating `/api/dashboard`, `/api/bandit`, `/api/cli-pool`, `/api/spend`, `/api/goals`, `/api/cliproxy/status`, `/api/learnings/summary` — same vanilla-JS-fetch pattern as `/dashboard`.
- No new dependencies, no vendor changes, no env flags (all read; matches existing loopback-open default).
- **Acceptance:** `curl http://127.0.0.1:8787/console` returns 200 HTML; new `tests/test_web_management_center.py` asserts each new `/api/*` route returns the `{ok: true}` contract envelope; `pytest tests/ -k web` full pass with no prior assertion changed.

### Phase 2 — Config read + write, with full safety scaffolding (the security-critical phase)
- `core/config.py`: atomic write, backup, `diff()` helper.
- `GET/POST /api/config`, `GET /api/config/diff`, `GET /api/config/backups`, `POST /api/config/rollback`, gated behind `SUPERAI_WEB_ENABLE_CONFIG_WRITE=1` **and** `SUPERAI_WEB_MANAGEMENT_TOKEN`.
- Redaction on GET, audit logging on every write.
- **Acceptance:** the three opt-in tests above, plus `test_config_write_atomic_and_backed_up` (monkeypatch a failure after temp-write, before rename; assert the original `config.json` is untouched), plus `test_config_diff_matches_written_change`, plus the redaction round-trip test.

### Phase 3 — Model registry write
- `POST /api/models` writing only to `~/.superai/config/models.json`, with `ModelInfo`-shape validation.
- **Acceptance:** `test_models_write_never_touches_repo_config` — repo-tracked `config/models.json` hash unchanged after a POST in a harness pointed at a fake `HOME`.

### Phase 4 — CLIProxyAPI admin embed
- `.gitattributes` commit, then `vendor/mgmt-ui/` bytes + manifest entry, then the `StaticFiles` mount at `/cliproxy-admin` behind `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN=1`, plus the ToS banner on `/console`.
- **Acceptance:** `python scripts/vendor_sync.py --check` passes (extend if it doesn't generalize to HTML entries); `test_cliproxy_admin_route_requires_opt_in` passes; manual browser smoke test against a real running CLIProxyAPI (documented as manual — not automatable without the Go binary in CI).

### Phase 5 — Docs
- New `docs/WEB_MANAGEMENT_CENTER.md` mirroring `docs/CLIPROXY_TRANSPORT.md`'s structure (enabling steps, env-var table, security caveats, ToS caution repeated).
- Cross-link from `docs/CLIPROXY_TRANSPORT.md`.

---

## Test Strategy

- **Backend:** `pytest`, following the existing pattern in `tests/test_pref_tt_web.py:48-60` — `fastapi.testclient.TestClient`, `pytest.importorskip("fastapi")`, `monkeypatch.setattr(Path, "home", ...)` to sandbox `~/.superai`. New tests go in `tests/test_web_management_center.py`, not appended to `test_pref_tt_web.py`.
  - **Isolation caveat from prior work:** `Path.home` monkeypatching does **not** isolate code that calls `os.path.expanduser`, which reads the environment directly. Check which mechanism each touched module uses before trusting the sandbox — this exact mismatch caused a CI hang once already.
- **No frontend test suite** — no frontend is built. `/console` is server-rendered vanilla JS matching existing pages; the vendored `management.html` is covered by the vendor-sync sha256 integrity check plus one manual smoke test, not unit tests (opaque third-party bytes).
- **Security-specific tests** carry the most weight given this work increases attack surface: the three opt-in tests, the redaction round-trip, and the atomic-write-survives-crash test.

---

## Risks, Unknowns, and Open Questions

**Decided in this plan (flag if you disagree):**
- Option (D) hybrid, scoped as described, over (B)/(C).
- Separate `SUPERAI_WEB_MANAGEMENT_TOKEN` for writes, distinct from `SUPERAI_WEB_TOKEN`.
- Writes target `~/.superai/config/*` only, never repo-tracked config files.
- Vendored `management.html` served as static bytes; the browser talks directly to the proxy — SuperAI's backend never proxies CLIProxyAPI traffic.
- `config/rules.md` / `strengths.md` out of scope for v1 web editing.
- Commit the built artifact rather than building in CI.

**Decided 2026-08-05 — `TASKBOARD.md` "Decisions" is authoritative; this list is a summary:**

1. **Feature-flag names — approved as proposed.** `SUPERAI_WEB_MANAGEMENT_TOKEN`, `SUPERAI_WEB_ENABLE_CONFIG_WRITE`, `SUPERAI_WEB_ENABLE_CLIPROXY_ADMIN`. T08 and T15 unblocked.
2. **Which ref to pin `management.html` to — its own separate tag**, independent of the proxy's `v7.2.116`. Never `main`.

**Correction — `.gitattributes` was NOT absent repo-wide.** This plan originally
stated it was, and treated the vendored `vega/*.min.js` bytes as unprotected.
Both claims were wrong. `vendor/.gitattributes` exists and contains `* -text`,
which applies recursively to everything under `vendor/` — including a future
`vendor/mgmt-ui/`. Verified: `git check-attr -a vendor/mgmt-ui/management.html`
→ `text: unset`, and `scripts/vendor_sync.py --check` → `4/4 files match their
pin`. What is absent is a **root** `.gitattributes`, which is a different thing
and does not affect vendored bytes. Consequence: T13 shrank from "create a
file, in its own commit, before the bytes" to a two-command verification, and
repo-wide source-line-ending normalization is deferred as a separate change
(see Q2 on the board).

**Still open — need Burhan's decision:**

3. **Does `scripts/vendor_sync.py` generalize to HTML entries**, or need a small extension? Not read during this investigation.
5. **The `config = Config()` singleton (`config.py:281`)** — which long-running processes import it, and does a web-issued write need an explicit reload hook? Determines whether "hot reload" can be claimed at all.
6. **Does a read-only status function exist in `code_intelligence.py` / `lsp_bridge.py`** for the `/api/code-intel` row, or must one be added there (a `core/` change, not a web-app change)?

---

## Effort Estimate

| Phase | Effort |
|---|---|
| 0 — Setup | 30 min |
| 1 — Native read console (**smallest useful slice**) | 2–3 hrs |
| 2 — Config read/write scaffolding | 4–6 hrs (atomic write + backup + diff + security tests dominate) |
| 3 — Model registry write | 1–2 hrs |
| 4 — CLIProxyAPI admin embed | 2–3 hrs (mostly vendoring mechanics + manual verification) |
| 5 — Docs | 1 hr |
| **Total** | **~11–16 hrs** across several sessions |

---

## Resolved after drafting

Four items listed as open in the original draft were verified directly and are now closed. All four resolved in the plan's favour; the tables above have been updated to reflect them.

| Original open question | Resolution |
|---|---|
| Does `core.cost_accounting` expose a callable read function for `/api/spend`? | **Yes** — `aggregate_costs()` at `cost_accounting.py:351`, alongside `estimate_call()` (`:331`) and `attach_cost_fields()` (`:421`). No new module function needed. |
| Does `core.goals_daemon` expose a read-only snapshot, or only CLI commands? | **Yes** — `status()` at `goals_daemon.py:133`, plus `load_state()` (`:59`) and `read_pid()` (`:110`). `/api/goals` is pure wiring. |
| Is there an LSP / code-intelligence module at all? | **Yes** — `src/core/code_intelligence.py`, `code_intelligence_advanced.py`, `lsp_bridge.py`. The row stays in the signal table; what remains unconfirmed is only whether a *read-only status* function exists inside them (now open question 6). |
| Is `.gitattributes` genuinely absent? | **Confirmed absent** repo-wide. The two-commit sequencing therefore starts by creating the file, and the pre-existing `vega` exposure is real (now open question 2). |

Also confirmed while resolving the above: `Config.save()` at `config.py:239-244` is indeed a plain `open()` + `json.dump` with no temp-file-then-rename, and the module-level `config = Config()` singleton at `config.py:281` exists as described. The atomicity gap in Phase 2 is real, not hypothetical.
