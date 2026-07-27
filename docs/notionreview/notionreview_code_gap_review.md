# Codebase gap review — coding errors, partial implementations, missing implementations

> Reviewed: `realburhanhusain/SuperAI` @ `99e680f` (master) · 27 Jul 2026 (21:30–22:15 +03)
> Owner: recotechai · Companion to `notionreview_actionitems.md` (the rolling backlog)

## Scope and method — read this first

What was done in this pass:

- Whole-repo marker scans on `master`: `NotImplementedError`, `TODO`, `FIXME`, `"not implemented"`, `placeholder`, `stub`, `while True` (tests).
- CI signal analysis across PRs #3, #4 and #7 (timings, job composition, what installs where).
- Full reads of: `pyproject.toml`, the new `ci.yml`, `tests/` directory listing (~100 test files), and two hang-candidate test files end to end.
- This builds on the two earlier deep review passes (~25 key files read in full, risky-pattern scans for `shell=True`, `eval`, `exec`, `pickle`, `yaml.load`, `os.system`).

What was **not** done, stated plainly:

- No code was executed. Every "tests unrun" caveat in the backlog still applies.
- CI job logs cannot be read with the available tools; two findings below are therefore **located by symptom, not by line**.
- ~230 files exist; most have not been read line by line. The findings below are what scans, CI evidence and targeted reads can support — each is labelled **verified** or **hypothesis**.

A structural observation that frames everything else: **this codebase contains zero `NotImplementedError`, zero code `TODO`s and zero `FIXME`s.** Incompleteness is not marked inline; it is tracked in the generated scorecards (`docs/V1_V6_UNIFIED_IMPROVED_SCORECARD.md` and generators under `scripts/gen_*.py`). Grep-based gap hunting therefore *understates* gaps — the scorecards are the real inventory, and by the project's own audit the V6 backlog stands at roughly **93 full / 98 foundation / 162 stub / 31 absent / 15 refuse-closed**.

---

## A. Coding errors

### A1. The blocking lint gate fails — something on the tree is genuinely broken *(verified failure, unlocated cause)*

The `Lint` job on PR #3 runs **only** `ruff check --select E9,F63,F7,F82` as its blocking step — syntax errors, undefined names, broken f-strings. It failed, completing in 10 seconds (install of ruff plus the run). The most probable reading is that ruff found real error-class violations somewhere on the tree; a step/environment failure cannot be fully excluded without the log.

**Resolution:** Phase 0 below. One local command locates every instance: `ruff check --select E9,F63,F7,F82 .`

### A2. The test suite fails on every OS×Python combination, and hangs on Windows *(verified failures; causes are hypotheses)*

All 9 matrix cells on PR #3 failed, including windows/3.11 — the only combination that was ever green historically. Two distinct signatures:

- **ubuntu/macos cells die in ~1 minute** — consistent with an install failure or a pytest **collection error** (an import crashing before any test runs), not with assertions failing.
- **windows cells run ~5.5 hours, then fail** — a hang-until-timeout signature. The same job hangs on PR #4 and on the Markdown-only PR #7, which **proves the hang pre-exists on `master`** and is caused by none of the open PRs.

Hang candidates (tests that spawn real subprocesses, daemons or pools): `test_daemon_deploy_n206.py` (16 KB), `test_goals_daemon_n206.py`, `test_terminal_pool.py`, `test_memory_concurrency.py`, and the `ProcessMux` respawn/restore tests. **Checked and cleared:** `test_tui_polish_conpty_atspi_restore.py` and `test_tui_live_input.py` were read end to end and are properly platform-guarded (`skipif` on non-Windows, conditional asserts) — recorded here so they are not re-suspected. `tests/` contains no `while True` and no `conftest.py`.

**Resolution:** Phase 0 locates it (`pytest --collect-only` for the fast failures; `pytest-timeout` for the hang); Phase 1 fixes it.

### A3. Second memory write path is unsanitized — `learning_engine.learn_from_step` *(verified by source read; still open)*

PR #6 sanitizes `central_memory.write_back`; the orchestrator also writes learnings via `learn_from_step`, which does not pass through it. `learning_engine.py` is 68 KB — too large to edit safely with whole-file writes (a previous attempt at that size truncated and committed invalid Python). PR #2's read-side envelope covers both paths at retrieval; this is the missing defence-in-depth half.

### A4. Fail-open budget gate in `web_app.py` *(verified earlier)*

Budget-check exceptions are logged as warnings and execution proceeds. A gate that fails open is a gate only when nothing goes wrong.

### A5. The "honest scorecard" generator contains a self-flagged wrong entry *(verified by scan)*

`scripts/gen_v1_v6_unified_improved_scorecard.py` contains `"M101": None,  # placeholder wrong`. The generator that produces the canonical completeness audit has a known-wrong entry annotated as such and left in place — a small defect with outsized irony, since this file is the ground truth everything else defers to.

### A6. Pervasive `except Exception: pass` *(verified pattern, class-level)*

Frequent throughout `src/core`. Individually defensible (best-effort paths), collectively this is how real failures become invisible — the same failure class as A4.

### A7. Runtime source-introspection audits break under packaging *(verified earlier)*

`foundation_safety.py` audits code with `inspect.getsource` at runtime; this breaks on refactor and entirely under wheel/bytecode installs. PR #3's `check_untrusted_appends.py` demonstrates the replacement pattern (AST check in CI).

### A8. Stale entry-point references outside `AGENTS.md` *(unverified — explicitly a to-check)*

PR #7 fixes `AGENTS.md` (`scli.main:app` → `scli.main:main`). Whether any other doc still references `app` has not been checked.

Already fixed or in flight, listed for completeness: `tool_bash` shell bypass (merged, PR #1), sandbox never wired into `run_shell` (PR #4 open), memory injection read path (PR #2 open) and write path half (PR #6 open), `.mcp.json` dead membrain entry (PR #5 open), `AGENTS.md` defects (PR #7 open).

---

## B. Partial implementations (real code, incomplete depth)

The project self-declares these honestly; the scan confirms the honesty is accurate rather than modesty:

| Area | State | Evidence |
| --- | --- | --- |
| ~98 "foundation" scorecard items | Core mechanism real; universality/UX/hardening missing | Scorecards + generators |
| `log_triage.py` | Python tracebacks only; Java/Node parsers absent (docstring admits docs previously over-claimed) | Module docstring |
| `lsp_bridge.py` | "stub_or_compile" mode — compile checks, not real LSP diagnostics | Module + V6 scorecard |
| `github_api.py` | Returns empty offline stubs without `GITHUB_TOKEN`/`gh` | Module |
| `ecosystem.py` web search | Tavily/Brave → DuckDuckGo Instant Answer → offline stub | Module |
| BackupManager | Encryption solid; restore/verify UX incomplete; key stored in plaintext | `SUPERAI_FINAL_SUMMARY.md` + backlog |
| Streaming (M027/V1-P5-2) | Real SSE only where providers support it; fallback chunking elsewhere | Scorecard notes |
| Session compaction (M029) | Decision/todo edge cases known-incomplete | Scorecard notes |
| Cost accounting (M002) | Some paths still use estimates/token placeholders when providers omit usage | Scorecard notes |

Note: the root-level `codes.md` ("ModelRegistry: Not implemented — build from scratch", etc.) is a **stale early planning artefact**, contradicted by current code and the current scorecards. It should be archived or deleted; treating it as current would misdirect anyone auditing the repo.

## C. No implementation (by design or by omission)

- `enterprise_stubs.py` — SSO/multi-tenant/etc. report "not configured"; P346–P365 are declared `stub`, P386–P400 `refuse`-closed on purpose.
- `parked_features.py` — P321–P385 catalogued as `stub_or_flag`/`vanity`; catalog entries, not features.
- `notion_stub.py` — dry-run stub unless an API key is set (G10).
- Roadmap-artefact modules that exist to report completion rather than do work: `foundation_complete.py`, `live_smoke_complete.py`, `v6_phase_status.py`, plus the scorecard generators' committed 240 KB outputs.
- ~31 scorecard items rated `absent` outright.

These are mostly *honest* gaps — the defect is not that they exist but that stub modules ship in the production package where they can be mistaken for features (`superai_agent` catalog lists `web_search` as "Tavily/Brave/stub").

---

## Resolution plan

Phased so that each phase unblocks the next. Owner tags: 🧑 = needs you (execution or authority), 🤖 = agent can do it, 🧑🤖 = your decision, agent executes.

### Phase 0 — Locate the two unlocated errors (🧑, ~30 minutes, blocks everything)

```bash
git checkout master && git pull
ruff check --select E9,F63,F7,F82 .              # locates A1 exactly
pip install -e ".[dev]" && pytest -q --collect-only   # exposes A2's fast-fail (collection) errors
pip install pytest-timeout
pytest -q --timeout=120 --timeout-method=thread   # exposes A2's hanging test by name
```

Alternatively read the Lint log: https://github.com/realburhanhusain/SuperAI/actions/runs/30250280427/job/89926485392. Paste the failing file/test names back and the fixes become mechanical.

### Phase 1 — Stabilize CI (🤖 after Phase 0 data; 🧑 merges)

1. Fix every located E9/F63/F7/F82 violation — one PR, no behaviour changes.
2. Add `pytest-timeout` to the `dev` extra and `--timeout=300` to the CI test job so a hang can never again cost 5.5 hours per cell and mask its own cause.
3. Fix or `skipif`-guard the hanging test(s) and any platform-specific collection failures.
4. Merge PR #3 (matrix) once green; then make `test` a required status check (🧑, repo settings).

### Phase 2 — Close the security work already in flight (🧑 run tests + merge; 🤖 follow-ups)

1. Run the four unrun suites (PR #2: 11, PR #4: 11, PR #6: 13, PR #1 post-merge: 10 tests).
2. Merge **#2 before #6** (stacked); #4, #5, #7 in any order.
3. Fix A3 (`learn_from_step`) via a delegated Copilot PR — the file is too large for safe whole-file writes (🧑🤖).
4. Add the outstanding CI rule: fail any new `subprocess.run(..., shell=True)` outside `os_shell.py` (🤖).

### Phase 3 — Correctness hardening (🤖, small independent PRs)

1. A4: make the `web_app` budget gate fail closed.
2. A5: fix or remove the `M101` placeholder in the scorecard generator and regenerate.
3. A6: replace `except Exception: pass` with narrow, logged handlers in the core execution path first (`orchestrator`, `tools_bridge`, `os_shell`, `central_memory`) — not a big-bang sweep.
4. A7: port the remaining `inspect.getsource` audits to AST checks in CI.
5. A8: sweep docs for `scli.main:app`; archive or delete the stale `codes.md`.
6. Encrypt the backup key (keyring + passphrase fallback) — carried from the backlog.

### Phase 4 — Partial/missing implementation triage (🧑🤖 policy, then 🤖 execution)

The 162 stubs and 31 absents need a policy decision, not 193 individual fixes. Proposed rule: for each item choose **implement / park / delete**, with a default of **park** (keep the catalog entry, mark it clearly) and **delete** for the roadmap-artefact modules that only report completion. Then:

1. Delete or clearly quarantine `foundation_complete.py`, `live_smoke_complete.py`, `v6_phase_status.py`, `enterprise_stubs.py`; stop committing generated scorecard artefacts (add to `.gitignore`).
2. Consolidate the duplicated clusters (TUI ~14 modules, memory ~11, routing ~9) — merge or delete, one cluster per PR.
3. Split `src/cli/main.py` (297 KB) into per-command modules — it is now blocking *fixes* (A3), not just review.
4. Re-generate the scorecards after each wave so the honest inventory stays honest.

### Standing verification rules (apply to every phase)

- Written ≠ verified: no fix is "done" until its test has been **run**.
- Every PR gets a `docs/notionreview/PR<N>_details.md`.
- A finding is labelled hypothesis until a read or a run confirms it — this review contains two located-by-symptom items (A1, A2) and says so.
