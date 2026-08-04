# Codex pending tasks — SuperAI

**Snapshot:** 2026-07-30  
**Rule:** Do not mark a task complete until production code, focused documentation, and offline tests exist. Automatic CI is intentionally disabled; run the relevant protected suite ad hoc before merge.

## Immediate: reconcile the source of truth

- [ ] **T0 — Reconcile Code Intelligence scorecard evidence (P0).**
  - Current `master` contains the Code Intelligence modules and the historic commits `35c5b946`, `7a4c9ab`, and `9b46670`.
  - The generated scorecard nevertheless reports N235 and N258 as 15% “stub” items. This is stale or its generator lacks evidence mappings; do not edit the generated rows by hand.
  - Inspect `scripts/gen_v1_v6_unified_improved_scorecard.py`, add durable evidence mappings for the implemented modules, docs, and tests, regenerate the scorecard, and verify the summary counts.
  - Acceptance: generated output accurately distinguishes completed scope from remaining scope, and cites real tests/docs.

- [x] **T1 — Preserve unrelated in-progress work (P0). RESOLVED 2026-08-04.**
  - Was: working tree had changes to `docs/PUBLIC_SURFACE_COVERAGE.md`,
    `docs/public_surface_coverage.json`, and untracked `probe.tmp` that were not
    made for this task; do not stage, discard, or fold these into Codex work.
  - Outcome: the two doc files are no longer pending (last touched by `236ce21`
    / `aa78a02`). `probe.tmp` was a 22-byte contract-probe leftover — deleted and
    ignored (`607bd84`), with the underlying harness leak filed as **T8** below.
    `pr_changes.diff` was a 30.5KB saved review diff whose content is fully
    merged (`_sanitize_for_memory`, `sandbox_argv`, `_run_in_container`,
    `_unattended_side_effects_allowed`, `neutralize_delimiters`,
    `wrap_untrusted_block` are all present in the tree; the `central_memory`
    half is `cb9d4fe`) — deleted, backed up outside the repo first.
  - Caution for anyone re-checking that diff: `git apply --check --reverse`
    **fails** on it, which reads as "contains unmerged work". It does not. The
    patch was cut on 30 July and surrounding context has drifted, so hunks no
    longer match positionally. Grepping for the added symbols is what answers
    the question.
  - The general instruction still stands: keep commits path-scoped and leave
    unrelated working-tree changes alone.

## Code Intelligence follow-up

- [ ] **T2 — Complete N235 with compiler/language-server-grade reachability (P1).**
  - Existing work provides conservative AST/local candidates and a bundled multi-language scanner. It deliberately does not prove whole-program reachability.
  - Add an optional LSP/compiler analysis layer with explicit capability detection and graceful fallback. Start with Python, then TypeScript/JavaScript; add Go, Rust, Java, and C# only when their toolchains are available.
  - Model import resolution, inheritance/overrides, decorators, reflection/dynamic imports, framework entry points, and workspace/package boundaries. Keep findings advisory; never auto-delete source.
  - Add fixtures for each protected construct and false-positive regression tests.
  - Acceptance: supported languages report provider/capabilities; unsupported hosts report a precise non-failure reason; test cases demonstrate fewer false positives than the conservative scanner.

- [ ] **T3 — Resolve language-server installation/runtime blockers (P1 prerequisite).**
  - Prior npm language-server installs hung despite a successful registry ping. Go and Rust toolchains were absent; no Python/TypeScript/Go/Rust/Java/C# language server was confirmed installed.
  - Diagnose npm/proxy/cache/process behavior without deleting global state. Prefer isolated installs. Install only the servers/toolchains needed by the chosen T2 language phase and record exact versions.
  - Acceptance: each enabled provider passes a small real workspace probe within a bounded timeout; failures are surfaced in diagnostics rather than hanging MCP/CLI calls.

- [ ] **T4 — Validate N258 incremental-index correctness under real change scenarios (P1).**
  - The implementation includes cache metadata, integrity verification, rename/delete handling, and metrics, but it needs durable scorecard evidence.
  - Add/retain tests for rename, deletion, content changes with preserved timestamps, cache schema upgrade, corrupted cache, and maximum-file limits. Document cache invalidation and `--verify-content` cost.
  - Acceptance: focused tests pass and the scorecard generator recognizes their evidence.

## Product-quality and backlog control

- [ ] **T5 — Run the protected suite ad hoc and record the exact command/result (P1).**
  - CI is intentionally disabled. Execute the full protected suite locally before merging substantive work, with a timeout and captured failure triage.
  - Acceptance: passing output is linked from the PR/task evidence, or every failing test has an owner and root cause.

- [ ] **T6 — Triage the remaining strict-scorecard backlog (P2).**
  - Current generated scorecard: 253 incomplete, 3 host-gated, and 15 refuse-closed items. This is a portfolio, not one implementation task.
  - Group incomplete items by dependency and product value; select the next small batch with explicit acceptance criteria. Do not bulk-promote heuristic “stub” rows merely because a nearby module exists.
  - Acceptance: a prioritized, scoped batch is approved and represented by individual tasks/PRs.

- [ ] **T7 — Close or explicitly defer the three host-gated items (P2 / user-dependent).**
  - M089, MOS-N8, and V1-P99 need live-key/vendor proof according to the scorecard.
  - Prepare safe offline harnesses; request credentials and an approved live-test window before executing any paid/external calls.
  - Acceptance: live evidence is recorded, or each row remains correctly host-gated with its dependency stated.

## Probe harness hygiene

- [ ] **T8 — Stop `probe_cli_contracts.py` writing into the repo root (P2).**
  - `scripts/probe_cli_contracts.py` drives commands with the `cli_fixtures`
    `PLACEHOLDER_TEXT` (`"superai-contract-probe"`, `src/core/cli_fixtures.py:28`).
    Some probed command takes a path argument and writes that string to
    `probe.tmp` in the repo root; nothing cleans it up, so it reappears after
    every probe run and shows as untracked for every session on this repo.
  - This contradicts a stated invariant: `cli_fixtures.py:86` says probe
    fixtures live outside the repo, and `"diff-edit"` is explicitly exempted at
    `cli_fixtures.py:91` on the grounds that "probe fixtures live outside the
    repo". Whichever command produced `probe.tmp` is not honouring that.
  - Find the responsible fixture by re-running the probe on a clean tree and
    watching for the file, or by grepping `cli_fixtures.py` for params that
    resolve to a bare filename rather than a temp path. Point it at a temp
    directory, and have the probe assert the repo tree is unchanged when it
    finishes — a harness that silently writes into the workspace it is
    measuring can also perturb what it measures.
  - `/probe.tmp` was added to `.gitignore` (commit `607bd84`) so the noise stops
    now. That hides the symptom deliberately; this task is the cause. Remove the
    ignore rule once the harness stops producing the file.
  - Acceptance: a full probe run leaves `git status` clean on a clean tree, and
    a test covers it.

## Operating checklist for every task

1. Branch from current `master`; do not overwrite unrelated working-tree changes.
2. Implement the smallest complete vertical slice (code, docs, focused tests).
3. Run focused tests, then the protected suite ad hoc for substantive changes.
4. Update the scorecard through its generator when evidence changes.
5. Commit only owned paths with `Codex / GPT-5` attribution, push, open/review PR, and merge only with explicit approval.
6. Save material decisions and blockers through the four-layer memory workflow.