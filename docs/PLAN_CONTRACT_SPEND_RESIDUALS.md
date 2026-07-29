# Plan — close 5 of the 11 near-done residuals (contract + spend + cost spine)

**Created:** 2026-07-28
**Scope source:** `docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md` § 2 INCOMPLETE (11 rows at 80–90%)
**Branch assumption:** work lands on a new branch off `master`; `codex/ci-gap-remediation-20260728` is owned by another agent and is not modified here.

---

## The 5 selected

| # | ID | Title | Now | Scorecard "still incomplete" |
|---|----|-------|----:|------------------------------|
| 1 | **V1-P1-1** | Stable result contract | 85% | Not all surfaces |
| 2 | **V1-P1-3** | Budget hard-stop foundation | 85% | Universal ceiling incomplete |
| 3 | **V1-P1-4** | Cost fields on results | 85% | Accuracy gaps |
| 4 | **V2-A4** | Result contract on tool/agent paths | 85% | Universal CLI incomplete |
| 5 | **V3-A4** | Contracts on more board APIs | 85% | Not all APIs |

### Why these five

They are the **only subset of the 11 that is fully closeable offline** and they share one
mechanism. Every one of them reduces to the same missing capability:

> *an authoritative, machine-generated enumeration of public surfaces, and a
> zero-tolerance assertion that each one is wrapped.*

Build that enumerator once and all five rows move together. The alternative pairing
(V2-B3 smart compact + V3-D1/V4-S3 bandit continuity + V2-C5 graph HTML) is four
unrelated features with four separate harnesses.

### Why not the other six

| Excluded | Reason |
|----------|--------|
| V1-P5-2, MOS-S1 | Both say "real provider SSE" — needs live keys. Same blocker as the 3 HOST-GATED rows (M089/MOS-N8/V1-P99). Not closeable offline. |
| V3-D1, V4-S3 | Bandit continuity; real but unrelated mechanism, and the Grok board flags a live double-count risk on `post_call`. Separate plan. |
| V2-B3, V2-C5 | Session-compact edge cases and legacy HTML graph. Genuinely independent; lowest coupling to the rest. |

---

## Ground truth established before planning (verified, not assumed)

| Finding | Evidence |
|---|---|
| `budget_precheck` / `budget_gate` appear **0 times** in `src/cli/main.py` — across 8581 lines and 255 command decorators. CLI spend gating today happens only underneath, at `ModelCaller` → `call_lifecycle.pre_call`. | `grep -c` on `src/cli/main.py` |
| `emit_public` / `render_public` appear **66 times** — so contract coverage is partial-by-construction against 255 commands (many are non-spend subcommands, but the ratio is unproven either way). | same |
| `verify_top_commands_registered` returns `ok` when **`len(missing) <= 5`** — a completeness check with five slots of built-in slack. | `src/core/public_surface.py:275` |
| `smoke_contracts_offline` validates **hand-constructed sample dicts**, not real handler output. It cannot detect an unwrapped surface, by design. | `src/core/contract_registry.py:69-95` |
| The estimate-provenance field exists **three times under three names**: `cost_source` (`usage`/`estimate`/`zero_local`) from `cost_accounting`, `src` (`registry`/`registry_io`/heuristic) from `rates_for_model`, and `estimate_source` at `board_preflight.py:49`. `audit_m002` already asserts on `estimate_source_wrong`. | `cost_accounting.py:51,239,451`, `board_preflight.py:49` |
| `budget_precheck` defaults to a hardcoded **`estimated_usd=0.1, tokens=500`** and never consults the model registry even when the model is known. | `src/core/spend_guard.py:14-15` |
| `SPEND_PATHS` is a **hand-maintained list of 12+ dicts**; `audit_m001` proves them with `inspect.getsource`, which breaks under wheel/bytecode install. | `foundation_safety.py:23,168` |
| **Correction to the 07-27 review (item A4):** the `web_app.py` budget gate does **not** fail open. It logs a warning, then fails **closed** with `error_code: budget_internal` whenever `live` is true; it only proceeds on the mock path, which cannot spend. Dropped from scope. | `web_app.py:254-272` |

---

## Two gates — read this before writing any exit criteria

The strict bar requires code **+** docs **+** tests. The test pillar is currently
unavailable to us: as of the 2026-07-27 review, `ruff --select E9,F63,F7,F82` fails and
**all 9 CI matrix cells fail**, with Windows cells hanging ~5.5h to timeout — proven
pre-existing on `master` and caused by none of the open PRs. `TASKBOARD.md` records the
latest restart reaching 149 passing before an explicit-worker ordering fix.

Therefore:

- **Gate A — in scope here.** Production code + docs + new per-item tests, each named
  test file passing when run in isolation (`pytest tests/<file> -q`). This is the whole
  deliverable of this plan.
- **Gate B — explicitly NOT in scope.** Promotion of any scorecard row to 100%. Gate B
  unblocks only when `codex/ci-gap-remediation-20260728` lands a clean full protected
  suite. Promoting on isolated-test evidence is exactly the failure this repo keeps
  repeating (AGY's `DONE` wave headers over ~45 unchecked leaf boxes; 266 `COMPLETE`
  rows asserting "fully tested" with no green suite since at least 07-25).

**No row in `V1_V6_UNIFIED_IMPROVED_SCORECARD.md` is edited by this plan.**

---

## Design decision: precheck vs. record ownership

Wiring `budget_precheck` into CLI commands risks double-counting against the existing
`ModelCaller.pre_call` gate. Settle it once, here:

> **The CLI layer may only PRE-CHECK. It must never RECORD.**
> `budget_precheck` at the CLI is a *pre-flight estimate block* — it asks
> "could this command plausibly exceed the ceiling?" and refuses early.
> `ModelCaller` / `call_lifecycle` remain the **sole** owner of `budget_record`,
> because only they know actual token usage.

Consequences to enforce in review:
- No new call to `budget_record` outside `call_lifecycle` and the existing `web_app`
  post-run path.
- `emit_public(..., record_spend=True)` must not be added to any command that also
  routes through `ModelCaller`. Audit the existing 66 call sites for this before adding.
- A CLI precheck that blocks must return the contract envelope and exit **without**
  recording anything.

---

## Phase 0 — Surface enumerator (the shared foundation)

Everything else depends on this. New module: `src/core/surface_inventory.py`.

**Must be AST/introspection-based over the Typer app, not a hand-maintained list.** The
existing hand-maintained registries (`SPEND_PATHS`, `TOP_30_COMMANDS`,
`JSON_CAPABLE_COMMANDS`) are declarations of intent that drift silently; that drift is
the root cause of all five rows.

- `enumerate_cli_surfaces()` — walk `app` plus all 20 sub-`Typer` apps
  (`config_app`, `learning_app`, `kg_app`, `session_app`, `ontology_app`, `dataset_app`,
  `capture_app`, `test_app`, `check_app`, `sym_app`, `budget_app`, `budget_cmd_app`,
  `completion_app`, `git_app`, `pi_app`, `sec_app`, `otel_app`, `cloud_app`,
  `host_hook_app`) → full command paths.
- `enumerate_mcp_surfaces()` — registered MCP tools from `mcp_server`.
- `enumerate_http_surfaces()` — FastAPI routes from `cli/web_app.py`.
- Each surface classified: `spend` | `mutating` | `read_only` | `interactive`.
- **Explicit exemption file** — `docs/SURFACE_EXEMPTIONS.md`, one line per exempt
  surface **with a stated reason**. Silent skips are forbidden; an unlisted, unwrapped
  surface is a test failure.

**Also in Phase 0:** fix `verify_top_commands_registered`'s `len(missing) <= 5` to
`len(missing) == 0`. Expect this to turn something red — that red is the point.

**Tests:** `tests/test_surface_inventory.py` — enumerator finds every known command;
a deliberately-added unwrapped fixture command is detected (proves the detector detects).

---

## Phase 0 — RESULT (2026-07-28)

Delivered: `src/core/surface_inventory.py`, `docs/SURFACE_EXEMPTIONS.md`,
`tests/test_surface_inventory.py` (19 passing), plus the
`verify_top_commands_registered` repair in `src/core/public_surface.py`.

**Baseline the enumerator reports — 315 public surfaces:**

| | CLI | MCP | HTTP | Total |
|---|---:|---:|---:|---:|
| Surfaces | 255 | 24 | 36 | **315** |

| Classification | Count |
|---|---:|
| read_only | 251 |
| **spend** | **37** |
| mutating | 18 |
| interactive | 9 |

| Coverage | Count |
|---|---:|
| Wrapped (contract envelope) | 59 |
| Exempt with a stated reason | 25 |
| **Uncovered** | **229** |
| — of which classified `spend` | **26** |

That 26 is the real size of the V2-A4 / V3-A4 gap, and it is the first time
the number has been derived rather than asserted.

**Defects found by the enumerator (none were on any board):**

1. **`verify_top_commands_registered` was a tautology, not merely slack.** The
   known plan was to change `len(missing) <= 5` to `== 0`. Reading it, `missing`
   was computed against `known = top_commands() | TOP_30_COMMANDS | names` —
   and `expected` *is* `TOP_30_COMMANDS`, so no expected name could ever be
   absent. It returned ok for an app with zero TOP_30 commands registered.
   Now computed against registered names only; `test_top30_check_is_not_a_tautology`
   hands it an empty app and asserts all 30 report missing.
2. **Three CLI commands are registered twice** — `debate`, `onboard`, `profile`
   (handlers at `main.py:3345`, `5610`, `4733`). Click keeps the last
   registration, so those three earlier handlers are unreachable dead code.
   Confirmed against the resolved Click command map.
3. **`SPEND_PATHS["web_api_run"].module` is `cli.web_app`, which does not
   import.** The installed package is `scli` (`src/cli` → `scli`). A registry
   row pointing at a non-existent module proves nothing about the path it
   claims to cover. (`tests/test_moscow_100.py:45` has the same stale import.)
4. **`AGY board vs. reality on `SPEND_TOOLS`.** `TASKBOARD_AGY.md:199` lists 11
   spend tools; the live set has **4** (`superai_run`, `superai_ask_session`,
   `superai_cli_parallel`, `superai_cli_run`). Not resolved here — flagged for
   Phase 2, since it changes what "MCP spend parity" means.

**MCP dispatch audit (clears part of AGY A1.4 "no raw handler bypasses wrap"):**
`_call_tool_impl` has exactly one caller in the tree (`mcp_server.py:629`), and
that call sits inside the closure `call_tool` passes to `wrap_mcp_tool`
(`mcp_server.py:636`). The HTTP bridge reaches it the same way —
`web_app.mcp_http` → `handle_request` → `call_tool` (`mcp_server.py:584`). All
24 MCP tools are therefore genuinely wrapped, and all 24 are safety-classified.
This is recorded as an audit with a re-check command in the code, not as an
assumption.

**Two `SPEND_PATHS` rows carry a prose label instead of a dotted module path**
(`bakeoff_compare`, `nl_ask_run`). Reported separately as `spend_paths_freeform_module`
rather than as stale, because reporting them as stale would be a false alarm —
the same disease the enumerator exists to cure.

**Deliberately not done in Phase 0:** nothing is wrapped and no scorecard row is
touched. The enumerator reports; Phase 1 enforces.

### Phase 0 residuals — closed 2026-07-29

Every defect Phase 0 recorded but did not fix is now fixed.

| Was | Now |
|---|---|
| 3 commands registered twice; earlier handler unreachable | **Renamed, not deleted.** Each pair was two *different* features colliding on one name, so deleting would have destroyed working code. `debate` (agentic multi-model, `--models`/`--rounds`) → `debate-models`; `onboard` (host-tools + Postgres setup wizard) → `onboard-wizard`; `profile` (config profile key) → `profile-config`. All six commands are now reachable. |
| `SPEND_PATHS["web_api_run"].module` = `cli.web_app`, unimportable | → `scli.web_app`. Two rows carrying a prose label (`core.a / b`) split into `module` + a new `also` field, which the checker validates too so it cannot become a hiding place. Both disagreement buckets are now empty. |
| `tests/test_moscow_100.py:45` imported `cli.web_app` | → `scli.web_app`. This test had been **skipping on every run** with the false reason "web extras not installed" while they were installed. It now executes and passes — the M6 web status contract had never actually been tested. |
| `TASKBOARD_AGY.md` waves A1–A5 marked `[x] DONE` over ~45 unticked leaves | Demoted to `[~] partial` with a dated note explaining that the leaves were right and the headers were wrong. "Last session" rewritten from "Still open: None" to the measured gap list. |
| `TASKBOARD_AGY.md:199` listed 11 `SPEND_TOOLS`; live set has 4 | Corrected, with the 7 non-existent names spelled out and the verification command recorded. |
| `gen_v1_v6_unified_improved_scorecard.py` held a dead `V6_SHOULD_COMPLETE = {"M101": None}` self-annotated "placeholder wrong" | Removed. Checked first: `M101` is not an ID in the source inventory at all — the V6 Must range ends at M100 and the Shoulds start at S101. Nothing was dropped from the scorecard, so it needs no regeneration and Gate B is untouched. |

**Coverage impact:** un-shadowing three commands briefly pushed uncovered 93 → 94
and uncovered-spend 3 → 4, because `debate-models` had been carrying hidden
coverage debt that only existed once the command became reachable. It was then
wrapped with `render_public` (Rich panels for humans, envelope under `--json`),
returning both figures to 93 and 3. Net: three restored features at no coverage
cost.

**New regression guards:** `test_no_shadowed_commands_on_the_real_app`,
`test_renamed_shadowed_features_are_reachable`, `test_spend_paths_modules_all_import`.

---

## Phase 1 — V1-P1-1 + V2-A4 + V3-A4: contract universality

These three are one job at three altitudes (core CLI / tool+agent / board APIs).

1. Replace `smoke_contracts_offline`'s synthetic samples with **real handler
   invocation** under mock, driven by the Phase 0 enumerator + `CliRunner`.
   Keep the old function as `smoke_contracts_synthetic()` so nothing that imports it breaks.
2. Assert every `REQUIRED_KEYS` field (`ok`, `status`, `mock`, `dry_run`, `model_chain`,
   `tokens`, `estimated_cost_usd`, `members`, `memory_ids`, `contract`) on each
   non-exempt surface's real output.
3. Wrap what the enumerator reports unwrapped — `emit_public` / `render_public` for CLI,
   `ensure_public_result` for library/board entrypoints.
4. Board APIs (V3-A4): normalize council / compare / bakeoff **member-level** results,
   not just the outer envelope.
5. Streaming: document that the chunk path is uncontracted by design and only the final
   aggregate carries the envelope (`call_stream_complete` already does this).

**Docs:** new `docs/PUBLIC_SURFACE_COVERAGE.md` with the generated matrix.
**Tests:** `tests/test_surface_contract_coverage.py` — zero-tolerance, parametrized
over the enumerator so a newly added command fails CI until classified.

---

## Phase 1 — RESULT (2026-07-29)

Delivered: `public_surface.contract_payload` + `contract_console`, the
`contract_middleware` in `web_app.create_app`, `contract_registry.invoke_cli_contracts_offline`,
`scripts/probe_cli_contracts.py`, `tests/test_surface_contract_coverage.py`
(23 tests). Total across Phases 0–1: **41 passing**.

### Coverage movement — read both columns, not just the first

| | Before Phase 1 | After |
|---|---:|---:|
| Wrapped (**static**: handler calls a wrapper) | 59 | **206** |
| Uncovered (static) | 229 | **93** |
| Uncovered **spend** (static) | 26 | **3** |

**The static number is an upper bound and must not be quoted alone.** It says a
handler calls a wrapper; it does not say a conforming envelope reached stdout.
A command can call `print_json` with a *list*, which `contract_payload` passes
through untouched by design — statically wrapped, no envelope printed. That is
the same declare-vs-derive drift that produced `SPEND_PATHS` and
`TOP_30_COMMANDS`, and it would be embarrassing to rebuild it inside the module
written to catch it.

So the dynamic sweep is reported beside it, and `disagreements()` now carries
`static_wrapped_but_probe_failed` — any command the inventory calls wrapped
that the probe caught printing no envelope. `test_static_wrapped_claim_agrees_with_the_probe`
fails if that list is ever non-empty.

**What is actually proven, from 210 invokable read_only commands:**

| Evidence | Count | Meaning |
|---|---:|---|
| **Proven** | 83 → 90 | Ran and printed a conforming envelope |
| **Unproven** | 87 + 7 | Needs an argument (87) or hangs (7); no evidence either way |
| **Failing** | 28 → 21 | Ran and printed no conforming envelope |
| Skipped | 5 | Uninvokable, each with a reason |

41% of the sweep is `usage-error` — those commands have *no* contract evidence
in either direction. Anyone reading "206 wrapped" should not infer 206 proven.

### Two seams instead of 284 hand-edits

`src/cli/main.py` prints results through `console.print_json(data=...)` at **264
call sites**, and `web_app` has 20 uncontracted `/api/*` handlers. Editing each
one is 284 chances to change behaviour by hand, and a partial job is
indistinguishable from a finished one.

- **CLI:** `console` is now `public_surface.contract_console()` — a `Console`
  subclass whose `print_json` contracts every `data=` dict. `main.py` has
  exactly one module-level `Console`, so this is a complete seam, and a
  `console.print_json` added tomorrow is contracted the day it is written.
- **HTTP:** a response middleware contracts every `application/json` body under
  `/api/*`. Deliberately narrow — `POST /mcp` is JSON-RPC (fixed by spec,
  contracted at the tool layer), `HTMLResponse` routes pass through, and bare
  arrays are left alone rather than silently retyped.

Both seams are load-bearing for the coverage numbers, so both have a test that
fails if they are removed: `test_cli_console_uses_the_contract_seam`,
`test_main_has_a_single_console`, `test_http_contract_middleware_is_installed`.

### Real invocation replaces synthetic samples

`smoke_contracts_offline` validates dicts it constructs itself — it passes
whether or not any real handler is wrapped. It is kept (other modules import
it) but its docstring now says exactly what it does and does not prove.
`invoke_cli_contracts_offline` runs actual commands and parses actual stdout.

### Full sweep — 210 read_only commands, one subprocess each

| Outcome | Count |
|---|---:|
| pass | 83 |
| usage-error (needs an argument; not a contract failure) | 87 |
| no-json (prints Rich tables only) | 20 |
| json-array (bare list, no envelope) | 7 |
| **hang** | **7** |
| missing-fields | 1 |
| skipped, with reason | 5 |

Written to `docs/PUBLIC_SURFACE_COVERAGE.md`.

### 7 commands hang — hand this to the CI work

`data-schema`, `diagnose`, `foundation-check`, `gates`, `learning distill`,
`metrics`, `reflect` never returned within 20s and were killed. `gates` is in
`TOP_30_COMMANDS`. One root cause is identified: `model_discovery._http_json`
opens a socket to Ollama on localhost and blocks on connect — a network call on
a path that is supposed to be offline. This is a strong candidate for the ~5.5h
Windows CI timeout, which no board or review had located.

A subprocess per command is why these are data rather than a stalled suite. The
in-process harness is deliberately restricted to a small sample for the same
reason.

### Phase 1 tail — closed 2026-07-29

| | After seams | Now |
|---|---:|---:|
| Uncovered surfaces (static) | 93 | **74** |
| Uncovered **spend** surfaces | 3 | **0** |
| Probe: emitted a conforming envelope | 87 | **105** |
| Probe: printed no JSON | 24 | **6** |
| Static-wrapped but probe-failed | 6 | **2** |

**Zero uncovered spend surfaces.** `council`, `cli-parallel` and `smoke-providers`
were wrapped with `render_public` — Rich output for humans, envelope under
`--json`. Every surface that can cost money is now machine-readable.

**19 Rich-table-only commands wrapped:** `version`, `backup`, `backup-status`,
`backup-verify`, `budget command list`, `conflicts`, `constitution`, `discover`,
`exit-codes`, `git explain-pr`, `history`, `ingest`, `learnings`, `list-models`,
`list-skills`, `proposals`, `provider-health`, `restore`, `routing-stats`. The
two early-exit paths (`restore` and `ingest` with no argument) now emit a
contracted failure with `error_code: invalid_input` instead of bare red text.

**`memory-ttl` crash fixed.** `TypeError: can't subtract offset-naive and
offset-aware datetimes` — a stored timestamp without a UTC suffix parsed naive,
and the subtraction sat outside the `except ValueError`, so one bad row took the
whole command down instead of being skipped. Seven regression tests in
`tests/test_memory_gdpr_ttl.py`.

**Classification bug found by its own side effects.** `backup` was classified
`read_only`, so the sweep invoked it on every run — creating a real encrypted
archive each time, 211 times over. `create_backup`, `restore_backup`,
`restore_from_cloud`, `apply_retention` and `sync_to_cloud` are now
`MUTATING_MARKERS`, which excludes those commands from the read_only sweep.

### Derived argument fixtures — 2026-07-29

The 87 `usage-error` commands were the largest remaining gap: 41% of the surface
with no contract evidence in *either* direction. Hand-writing 87 fixtures would
have created exactly the kind of hand-maintained list this whole plan exists to
eliminate, so `core/cli_fixtures.py` **derives** them from Click's own parameter
metadata — required params, declared `Choice` types, the `a | b | c`
enumerations already sitting in help strings, and type defaults.

81 of 87 derive automatically. The other 6 are refused with a stated reason
(`browse` fetches a live URL, `shell` executes arbitrary commands, `backup-key`
touches the encryption key, and so on) — refusal, never a guess.

Fixture runs execute against a **throwaway HOME**. `Config` resolves its state
directory from `Path.home()`, so redirecting `HOME`/`USERPROFILE` means a
command invoked with synthesized arguments cannot write to the real
`~/.superai`. Without that, this pass would have mutated live state 80+ times
per sweep — the same mistake that had `backup` writing a real archive on every
run.

**The 87 unknowns resolved:**

| Outcome | Count |
|---|---:|
| Passed once given derived arguments | **38** |
| Ran and printed no valid envelope | **33** |
| No safe argument derivable (reason recorded) | **10** |
| Hang / other | remainder |

Probe-unproven dropped **95 → 28**. Commands proven to emit a conforming
envelope rose **101 → 136**.

The 33 `fail-with-fixture` commands are newly-visible genuine gaps — they were
always broken; nothing could see it while they hid behind "missing argument".
Eight of them are statically "wrapped", which is why
`static_wrapped_but_probe_failed` rose 2 → 8. **That rise is improved
visibility, not regression.**

### Newly-visible gaps closed — 2026-07-29

The 33 `fail-with-fixture` commands were the direct product of the fixture work:
commands that had always printed plain text on their not-found, empty-result and
success paths, invisible while they hid behind "missing argument". 17 are now
wrapped:

`budget command get`, `budget command set`, `config get`, `config set`,
`git suggest-branch`, `git suggest-commit`, `git resolve-conflicts`,
`set-strategy`, `set-supervisor`, `symbol search`, `triage-log`, `tt-list`,
`skill-promote`, `skill-rollback`, `prompt-injection scan`, `check lint`,
`security scan-secrets` (plus `memory-sync export`).

`skill-promote` and `skill-rollback` additionally gained `error_code: not_found`
on their failure paths, which previously exited 1 with only red text.

| | Before | After |
|---|---:|---:|
| Uncovered surfaces (static) | 74 | **57** |
| Probe: conforming envelope | 136 | **158** |
| Probe: `fail-with-fixture` | 33 | **17** |
| Probe: unproven | 28 | **22** |
| Static-wrapped but probe-failed | 8 | **7** |

### Phase 1 complete — 2026-07-29

The last 12 wrappable commands are done: `check critique`, `check license`,
`ci-fix`, `evolve`, `feedback`, `git-helper`, `profile-bundle`,
`prompt-injection wrap`, `proposal`, `skill`, `test impacted`, `capture stream`.

`proposal` additionally stopped raising a bare `KeyError` at an unknown id —
automation was getting a traceback where a `not_found` envelope belonged.

**The `kg` / `ontology` Postgres blocker is resolved without touching PR #10's
product decision.** `_kg_guarded` catches backend failures and emits
`error_code: backend_unavailable` with a hint naming `SUPERAI_KG_DSN`. PostgreSQL
is still the default and SQLite is still opt-in; what changed is that an
unreachable backend is now reported as a contracted failure rather than a raw
`psycopg.OperationalError` traceback. Six call sites are guarded, including
`get_default_graph()` itself in `ontology induce` — constructing the graph opens
the connection, so guarding only the query left the crash in place.

| Metric | Phase 1 start | Now |
|---|---:|---:|
| Uncovered surfaces (static) | 229 | **49** |
| Uncovered **spend** surfaces | 26 | **0** |
| Probe: conforming envelope | 0 (no invocation evidence existed) | **176** |
| Probe: printed no JSON | 24 | **0** |
| Probe: unproven | 95 | **20** |
| Static-wrapped but probe-failed | — | **5** |

### Zero uncovered surfaces — 2026-07-29

**The Phase 0 end-state is now literally true:** every public surface is either
wrapped or listed in `SURFACE_EXEMPTIONS.md` with a stated reason. The ratchets
`MAX_UNCOVERED_SPEND` and `MAX_UNCOVERED_TOTAL` are both **0**, so they are
invariants rather than bounds.

Two things got there:

**A 48-command false negative in the static scan.** `kg status` calls
`_print_kg`, which calls `emit_public` — genuinely wrapped, but a one-hop scan
saw only `_print_kg` and reported it uncovered. The whole `kg`, `capture`,
`dataset` and `learning` families were mislabelled, every one of which the
dynamic probe had been passing all along. `resolve_local_helpers` folds
locally-defined callees into each function's signal set, bounded at 3 hops and
iterated to a fixed point. Uncovered dropped 49 → 8 from that correction alone,
which is the clearest argument yet for keeping the static and dynamic views
side by side: the static view was wrong, and only the disagreement showed it.

**The last 8 wrapped or exempted:** `backup-key`, `propose`,
`completion install`, `diagnose`, `reflect`, `check upgrades`, `term-parallel`,
plus `mcp-serve` exempted (stdout is the JSON-RPC channel — anything else
printed there corrupts the protocol).

| Metric | Phase 1 start | Final |
|---|---:|---:|
| Uncovered surfaces | 229 | **0** |
| Uncovered **spend** surfaces | 26 | **0** |
| Wrapped | 59 | **300** |
| Exempt with a reason | 0 | 26 |
| Probe: conforming envelope | 0 | **176** |
| Probe: printed no JSON | 24 | **0** |

**Three stale `UNINVOKABLE` entries removed** — `serve`, `goals-daemon` and
`watch` named commands that do not exist, so they refused nothing while reading
as deliberate safety. Same failure mode as the stale `SPEND_PATHS` module
reference and the stale fixture override; `test_uninvokable_entries_name_live_commands`
now asserts every entry resolves.

### Still open after the tail

- **5 commands blocked by a regression, not by contract work** — `kg path`,
  `kg query`, `kg status`, `kg upsert-edge`, `ontology induce` all crash with a
  Postgres connection error. PR #10 (merged 2026-07-29) set
  `DEFAULT_KG_DSN = "postgresql+psycopg://localhost/superai"` and dropped the
  SQLite default, so every `kg` command fails on any machine without a
  passwordless local Postgres. Its CI check was green, so CI must provide one.
  Not fixed here: reverting or adding a fallback is a product decision on
  someone else's feature.
- **2 flaky probe readings** — `bandit` and `pref` emit complete envelopes when
  run standalone but fail inside the 211-command sweep. Both read mutable JSON
  under `~/.superai/`; likely another command rewrites that state mid-sweep.
  Bounded and named rather than excluded.
- **87 `usage-error` commands** — still need per-command argument fixtures. This
  is now the single largest gap: 41% of the sweep has no contract evidence in
  either direction.
- **6 hangs** — `data-schema`, `diagnose`, `foundation-check`, `gates`,
  `learning distill`, `reflect`.

### Remaining Phase 1 work

- **20 `no-json`** — commands that only print Rich tables. Each needs a result
  dict; no seam can invent one.
- **7 `json-array`** — need an envelope around the list (`audit`, and six others
  in `PUBLIC_SURFACE_COVERAGE.md`).
- **87 `usage-error`** — need per-command argument fixtures to prove their
  contract. Recorded, not dropped.
- **3 uncovered spend surfaces** — down from 26.

---

## Phase 2 — V1-P1-3: universal budget ceiling

1. Add `spend_precheck_for_command(name, model=None)` to `spend_guard` — resolves the
   estimate from the **model registry** when the model is known, falling back to the
   current flat default only when it is not (and labelling that fallback, see Phase 3).
2. Wire it into CLI commands the Phase 0 enumerator classifies `spend`, passing
   `command_name` so the S132 per-command ceilings actually bind. Today only
   council/bakeoff/compare pass a command name.
3. Grep campaign for direct provider calls bypassing `ModelCaller`:
   `rg "openai|Anthropic|httpx|requests\.(get|post)" src --glob "*.py"` — each hit is
   either routed through `ModelCaller`, added to `SPEND_PATHS`, or proven non-spend in
   the exemption file.
4. Rewrite `audit_m001` to consume the Phase 0 enumerator instead of
   `inspect.getsource`, killing the packaging fragility (A7). Follow the AST pattern
   already demonstrated by `scripts/check_untrusted_appends.py`.
5. Honor the ownership rule above: **precheck only, no new records.**

**Tests:** `tests/test_spend_ceiling_universal.py` — monkeypatch `budget_precheck` and
assert it is called for every `spend`-classified surface; assert `budget_record` call
count is unchanged from baseline (the anti-double-count guard).

---

## Phase 3 — V1-P1-4: cost field accuracy

This is **unify and propagate one field**, not add one.

1. Pick `estimate_source` as the single canonical name (it is already the one on a
   public contract, at `board_preflight.py:49`, and already asserted in `audit_m002`).
2. Map the existing producers onto it — `cost_source` and `rates_for_model`'s `src`
   become inputs to one resolver. Canonical values:
   `actual` (provider usage) > `registry` > `fallback`.
   Keep `cost_source` populated as a deprecated alias for one release.
3. Add `estimate_source` to the contract envelope wherever cost fields appear, so
   precision is never silently overstated.
4. Make `budget_precheck` pull registry rates when the model is known
   (removes the hardcoded `0.1 / 500`); when unknown, emit `estimate_source: fallback`.
5. Board preflight estimates use the registry per member model.

**Docs:** `docs/COST_ACCOUNTING.md` — estimate vs. actual table with the precedence rule.
**Tests:** extend `tests/test_cost_accounting_m002.py` — known model → `registry`;
unknown model → `fallback` and flagged; provider usage present → `actual` overrides.

---

## Sequencing

```
Phase 0  surface enumerator + exemptions + kill the <=5 slack   [blocks everything]
   ├── Phase 1  contract universality      (V1-P1-1, V2-A4, V3-A4)
   ├── Phase 2  budget ceiling             (V1-P1-3)      depends on P0 classification
   └── Phase 3  cost field unification     (V1-P1-4)      independent of P1/P2 after P0
```

Phases 1–3 are parallelizable once Phase 0 lands. Phase 2 and Phase 3 touch
`spend_guard.py` in different functions — coordinate or serialize those two edits.

---

## Definition of done (Gate A only)

- [x] `surface_inventory.py` enumerates CLI + MCP + HTTP surfaces (315), and
      **every one is wrapped or exempt with a reason** — 300 wrapped, 26 exempt,
      0 uncovered. Zero silent skips: reason-less exemption rows are ignored.
      This is the full end-state, not a partial one.
- [x] `verify_top_commands_registered` fixed — and it was a tautology, not slack.
- [x] Real-invocation contract coverage replaces synthetic samples
      (`invoke_cli_contracts_offline` + `scripts/probe_cli_contracts.py`).
- [ ] Every `spend`-classified surface pre-checks with a `command_name` — **Phase 2**.
- [ ] `audit_m001` no longer uses `inspect.getsource` — **Phase 2**.
- [ ] One canonical `estimate_source` on all cost-bearing contracts — **Phase 3**.
- [ ] `budget_record` call count unchanged from baseline — **Phase 2** (nothing in
      Phases 0–1 adds a `budget_record` call, so the invariant holds so far).
- [x] Test files pass in isolation: `tests/test_surface_inventory.py` (23),
      `tests/test_surface_contract_coverage.py` (23) — 46 total.
- [x] `PUBLIC_SURFACE_COVERAGE.md` + `SURFACE_EXEMPTIONS.md` written.
      `COST_ACCOUNTING.md` is **Phase 3**.
- [x] `TASKBOARD_AGY.md` false `DONE` headers (A1–A5) demoted to `[~] partial`;
      `SPEND_TOOLS` list corrected 11 → 4; "Last session" rewritten from
      "Still open: None" to the measured gap list.
- [x] **Scorecard untouched.** No row promoted. Gate B still blocked on a green
      full suite.

## Explicit non-goals

- Fixing the red CI / Windows hang (owned by `codex/ci-gap-remediation-20260728`).
- Any scorecard percent edit.
- The 6 non-selected residuals; the 3 host-gated rows; the 64 S-items / 88 N-items.
- The 85 anti-feature rows (P301–P385, P366, P368) that inflate the INCOMPLETE bucket —
  these should be **reclassified into REFUSE-CLOSED** by the generator, but that is a
  separate one-line change to `scripts/gen_v1_v6_unified_improved_scorecard.py` and is
  not bundled here.

## Known generator defect noted in passing (not in scope)

`scripts/gen_v1_v6_unified_improved_scorecard.py:168` defines
`V6_SHOULD_COMPLETE = {"M101": None,  # placeholder wrong}`. This dict is referenced
nowhere else in the file, and `M101` consequently appears in **no** section of the
generated scorecard — neither complete nor incomplete. It silently fell out of the 533.
