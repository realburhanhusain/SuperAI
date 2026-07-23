# AGY Handoff — Pending & Incomplete Findings

**Author:** Grok (memory roadmap track)  
**Date:** 2026-07-23  
**Repo:** `Documents/Personal/github/SuperAI`  
**Review tip when written:** `144bba5` (master; memory P1–P8 complete)  
**Audience:** AGY (scorecard / V1–V6 Musts & Shoulds)  
**Strict bar:** production code + thorough docs + full tests **and** product wiring (CLI/MCP/tool paths where claimed)

---

## 0. How to use this file

1. Treat this as a **work queue**, not a blame list.  
2. For each ID: **Done / Partial / Blocked** + concrete next steps.  
3. Re-run the verification commands in §8 after each fix.  
4. **Do not** claim scorecard COMPLETE until all three pillars + wiring pass under the strict bar.  
5. **Do not** edit memory-roadmap modules unless coordinated with Grok (see §1).

---

## 1. Coordination / file ownership (avoid conflicts)

### Grok owns (memory roadmap P1–P8) — leave alone unless coordinated

| Area | Paths |
|------|--------|
| Knowledge graph | `src/core/knowledge_graph.py`, `superai kg`, MCP `superai_kg_*` |
| Cognify | `src/core/cognify.py`, `superai cognify` |
| Session | `src/core/session_memory.py`, `superai memory-session` |
| Recall | `src/core/recall_router.py`, `superai recall` |
| Ingest | `src/core/ingest.py`, `superai ingest` |
| Ontology | `src/core/ontology.py`, `src/core/data/memory_ontology.yaml`, `superai ontology` |
| Datasets | `src/core/memory_dataset.py`, `superai dataset` |
| Capture P8 | `src/core/session_capture.py`, `superai capture` |
| Docs | `docs/KNOWLEDGE_GRAPH.md`, `COGNIFY.md`, `SESSION_MEMORY.md`, `RECALL.md`, `INGEST.md`, `ONTOLOGY.md`, `DATASETS.md`, `SESSION_CAPTURE.md`, `MEMORY_ROADMAP_COGNEE_GAPS.md` |
| Tests | `tests/test_*_p1.py` … `test_session_capture_p8.py` |

### AGY owns (scorecard)

`exit_codes`, `prompt_injection`, `git_helpers`, help/completion CLI, auto_test_runner, lint_typecheck, security_scan, log_triage, symbol_nav, pr_explainer, license_check, command_budget, and related scorecard docs/tests — plus any WIP (see §6).

### Shared caution

- `src/cli/main.py` and `src/core/mcp_server.py` are **shared**. Prefer additive commands only; re-read before editing; avoid deleting memory commands.  
- History: `0bba3bc` stripped unfinished AGY CLI from `main` that had been staged without modules. **CLI for AGY Musts was never fully re-wired** after modules landed (`07b67ac` did **not** change `main.py`).

---

## 2. Executive summary — what is still incomplete

| Priority | ID / theme | Status | Blocker |
|----------|------------|--------|---------|
| **P0** | CLI wiring for M080/M081/M082/M015/S116 | **Broken** | Tests expect commands that are **not registered** on Typer app |
| **P0** | `tests/test_cli_help_and_completion_m081_m082.py` | **8 failed** | `SystemExit(2)` / help missing command names |
| **P1** | M080 exit codes product-wide | **Partial ~80%** | Library + `public_surface` only; many CLI paths still hardcode `Exit(1)` |
| **P1** | M015 prompt injection in tool loops | **Partial ~60–70%** | Module not wired into MCP/agent tools; duplicates `injection_defense.py` |
| **P1** | M081 help quality | **Not closed** | No dedicated help/examples surface beyond Typer defaults |
| **P1** | M082 shell completion | **Not closed** | Only `add_completion=True`; no `completion show/install` commands |
| **P2** | Scorecard honesty for M080/M015/M081/M082 | **Stale / overclaimed** | Commit msgs say “close”; scorecard still **Complete? NO** (good); f0299f5 only promoted **S116** |
| **P2** | S116 git helpers CLI | **Library OK; CLI missing** | Unit tests pass; CLI tests fail |
| **P2** | Shoulds marked 100% (S105/S106/S114/S124/S108/…) | **Verify strictly** | Many are library+unit only; may lack CLI/MCP/agent hooks |
| **P3** | Uncommitted WIP S104/S109/S112 | **Not shipped** | Local only at handoff time |

**Memory track (Grok):** P1–P8 **done** on master — not AGY work; listed so you don’t re-open those gaps.

---

## 3. Critical finding — CLI never re-wired (P0)

### Evidence

Commit `07b67ac` (*feat(must): close M080…M015…S116*):

- Added: modules, docs, unit tests  
- **Did not modify** `src/cli/main.py`

Tests still assume:

```text
superai exit-codes
superai completion show --shell bash|zsh
superai completion install --shell powershell
superai git suggest-branch "..."
superai git suggest-commit "..." --scope cli
superai prompt-injection scan "..."
superai prompt-injection wrap "..." --label ...
```

**Re-verified 2026-07-23:** all 8 CLI integration tests **FAIL** (`SystemExit(2)`).  
Unit tests for `exit_codes` / `prompt_injection` / `git_helpers` **PASS**.

### Required fix (AGY)

1. Register Typer commands/groups on `scli.main:app` (or restore carefully from pre-`0bba3bc` if still in history).  
2. Ensure `--help` lists: `exit-codes`, `completion`, `git`, `prompt-injection`.  
3. Green:  
   `python -m pytest tests/test_cli_help_and_completion_m081_m082.py -q`  
4. Only then consider M081/M082/M015 (CLI surface) for scorecard movement.

---

## 4. Per-ID findings (landed Musts)

### M080 — Trustworthy process exit codes

| Pillar | Status |
|--------|--------|
| Code | **Yes** — `src/core/exit_codes.py` (OK/USAGE/BUDGET/…/INTERNAL) |
| Docs | **Yes** — `docs/EXIT_CODES.md` |
| Unit tests | **Pass** — `tests/test_exit_codes_m080.py` |
| Product wiring | **Partial** — used by `public_surface.emit_public` → `exit_code`; many CLI paths still `raise typer.Exit(1)` |
| CLI list command | **Missing** — `superai exit-codes` expected by tests, not registered |
| Scorecard | Still **Complete? NO**, ~80% — **accurate under strict bar** |

**Pending**

- [ ] Wire `from_result` / `from_exception` at main CLI exception boundary and major subcommands.  
- [ ] Map `error_code` values consistently across memory/foundation returns (already used in places).  
- [ ] Add `superai exit-codes` (or update tests if intentionally library-only).  
- [ ] Document/justify `status=="partial"` → `TIMEOUT` (surprising).  
- [ ] Fix type hint: `from_exception(exc: Exception)` but accepts `None`.  
- [ ] Do **not** mark 100% until process exits are systematically mapped (scorecard already notes “Not all process exits wired”).

---

### M015 — Prompt-injection defenses for tool loops

| Pillar | Status |
|--------|--------|
| Code | **Yes (library)** — `src/core/prompt_injection.py` |
| Docs | **Yes** — `docs/PROMPT_INJECTION_DEFENSE.md` (scorecard text still says docs NO — stale) |
| Unit tests | **Pass** — `tests/test_prompt_injection_m015.py` |
| Tool-loop wiring | **No** — not imported by `mcp_safety`, `agent_tools`, browser/fetch, or tool bridge |
| Overlap | **Yes** — pre-existing `src/core/injection_defense.py` (scan + sanitize + secret redact on tool results) |
| CLI | **Missing** — scan/wrap commands not registered |
| Scorecard | Still **Complete? NO**, ~70% |

**Pending**

- [ ] **Unify or chain** `prompt_injection` + `injection_defense` (one public API for tool loops).  
- [ ] Call scan/sanitize/wrap on: tool results, URL/file ingest paths, MCP untrusted args (as appropriate).  
- [ ] Policy: detect-only vs block vs wrap-and-continue — document and implement.  
- [ ] Wire CLI `prompt-injection scan|wrap` **or** drop CLI tests.  
- [ ] Expand patterns carefully; add tests for false positives/negatives.  
- [ ] Update scorecard docs pillar text after real wiring.  
- [ ] Do **not** claim “defenses for tool loops” until a real code path invokes them.

---

### M081 — High-quality `--help` and examples

| Pillar | Status |
|--------|--------|
| Code | Typer help exists globally; **no** dedicated help quality work proven |
| Docs | `docs/CLI_HELP_AND_COMPLETION.md` exists |
| Tests | **Fail** — help does not contain expected command names |
| Scorecard | Still **Complete? NO**, ~60% |

**Pending**

- [ ] Register missing commands (see §3) so help is accurate.  
- [ ] Add examples to high-traffic commands (help text / epilog).  
- [ ] Optional: `superai help <topic>` or rich examples doc linked from `--help`.  
- [ ] Green CLI tests + spot-check `superai --help`.

---

### M082 — Shell completion

| Pillar | Status |
|--------|--------|
| Code | `add_completion=True` only (pre-existing) |
| Docs | Partial in `CLI_HELP_AND_COMPLETION.md` |
| Tests | **Fail** — `completion show|install` not registered |
| Scorecard | Still **Complete? NO**, ~55% |

**Pending**

- [ ] Implement `superai completion show --shell {bash,zsh,powershell,fish}`.  
- [ ] Implement `superai completion install` (or honest “print snippet only” + docs).  
- [ ] E2E-ish tests that assert non-empty completion script output.  
- [ ] Document install paths for Windows PowerShell.

---

### S116 — Commit message + branch naming helpers

| Pillar | Status |
|--------|--------|
| Code | **Yes** — `src/core/git_helpers.py` |
| Docs | **Yes** — `docs/GIT_HELPERS.md` |
| Unit tests | **Pass** |
| CLI | **Missing** — tests expect `superai git suggest-branch|suggest-commit` |
| Scorecard | Marked **COMPLETE YES 100%** in improved scorecard |

**Pending / nits**

- [ ] Wire CLI group `git` for discoverability (or adjust tests if library-only is intentional).  
- [ ] If staying library-only, scorecard is acceptable for a “helpers” Should; CLI gap is polish.  
- [ ] Optional: integrate into `superai propose` / commit flow later.

---

## 5. Scorecard process issues (honesty)

| Observation | Detail |
|-------------|--------|
| Commit `07b67ac` message | Claims close M080, M081, M082, M015, S116 |
| Commit `f0299f5` message | Claims update completions for those IDs |
| Actual `f0299f5` diff | Only **S116** moved incomplete → complete (+1 COMPLETE count) |
| M080 / M015 / M081 / M082 | Remain **Complete? NO** in incomplete section — **correct** under strict bar |
| Risk | Future regen scripts marking 100% from “module exists” without wiring |

**Pending**

- [ ] Align commit messages with scorecard reality.  
- [ ] When closing Musts: move incomplete → complete **only** after CLI+integration green.  
- [ ] Refresh M015 docs line in scorecard (dedicated doc now exists; wiring still missing).  
- [ ] Prefer generator script updates over hand-editing both COMPLETE and INCOMPLETE sections inconsistently.

---

## 6. Landed Shoulds — verify / residual gaps

These were marked COMPLETE at 100% in scorecard after AGY commits `73a8751` and `6ac9f5d`. Under a **strict** bar, re-check wiring:

| ID | Module | Docs | Unit tests | Residual risks / pending checks |
|----|--------|------|------------|----------------------------------|
| **S105** | `auto_test_runner.py` | AUTO_TEST_RUNNER.md | yes | Stem matching can over/under-select; `pytest.main` from library is heavy; confirm CLI/agent trigger if claimed |
| **S106** | `lint_typecheck.py` | LINT_TYPECHECK.md | yes | AST-only (not mypy); “typecheck” name overstates; bare-except heuristics only |
| **S114** | `security_scan.py` | SECURITY_SCAN_HOOKS.md | yes | Regex secrets only; false positives; **hooks** name implies pre-commit/tool integration — confirm actually hooked |
| **S124** | `log_triage.py` | LOG_TRIAGE.md | yes | Python-centric frames; suggested fixes are templates; CLI? |
| **S108** | `symbol_nav.py` | SYMBOL_NAV.md | yes | Beyond-grep claim — verify quality vs simple AST/name index |
| **S110** | `pr_explainer.py` | PR_EXPLAINER.md | yes | Needs real git/gh context for E2E; offline tests may be shallow |
| **S115** | `license_check.py` | LICENSE_COMPLIANCE.md | yes | Confirm runs on new deps path (install/lockfile), not only API |
| **S132** | `command_budget.py` | COMMAND_BUDGET.md | yes | Confirm wired into spend_guard / CLI budget paths (S132 touched `main.py`) |

**Pending for AGY self-audit**

- [ ] For each YES row: run unit tests + one manual CLI/MCP path.  
- [ ] If only library+unit: either wire product entrypoints or lower percent / note “library complete, integration pending”.  
- [ ] S114 especially: if not hooked into edit/PR/CI, rename docs or add real hooks.

---

## 7. Uncommitted local WIP (not on origin at handoff)

Working tree had (do not lose; finish or stash):

| Likely ID | Paths |
|-----------|--------|
| **S104** | `src/core/self_critique.py`, `docs/SELF_CRITIQUE.md`, `tests/test_self_critique_s104.py` |
| **S109** | `src/core/ci_fixer.py`, `docs/CI_FIXER.md`, `tests/test_ci_fixer_s109.py` |
| **S112** | `src/core/dep_upgrade.py`, `docs/DEP_UPGRADE.md`, `tests/test_dep_upgrade_s112.py` |

**Pending**

- [ ] Finish implementation to strict bar (code+docs+tests+wiring).  
- [ ] Commit separately from memory work.  
- [ ] Do not mark scorecard complete before green tests + wiring.  
- [ ] Avoid colliding with Grok edits to `main.py` / `mcp_server.py` — rebase often.

---

## 8. Verification commands (copy/paste)

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI

# AGY Must unit tests (should stay green)
python -m pytest tests/test_exit_codes_m080.py tests/test_prompt_injection_m015.py tests/test_git_helpers_s116.py -q

# AGY CLI integration (currently RED — must go green after wiring)
python -m pytest tests/test_cli_help_and_completion_m081_m082.py -q --tb=short

# Help smoke
python -m scli.main --help
# expect: exit-codes, completion, git, prompt-injection once wired

# Should unit packs (spot-check)
python -m pytest tests/test_auto_test_runner_s105.py tests/test_lint_typecheck_s106.py tests/test_security_scan_s114.py tests/test_log_triage_s124.py tests/test_symbol_nav_s108.py tests/test_pr_explainer_s110.py tests/test_license_check_s115.py tests/test_command_budget_s132.py -q

# Do not break memory track
python -m pytest tests/test_knowledge_graph_p1.py tests/test_cognify_p2.py tests/test_session_memory_p3.py tests/test_recall_router_p4.py tests/test_ingest_p5.py tests/test_ontology_p6.py tests/test_memory_dataset_p7.py tests/test_session_capture_p8.py -q
```

---

## 9. Recommended AGY work order

1. **Wire CLI** for exit-codes / completion / git / prompt-injection → green `test_cli_help_and_completion_m081_m082.py`.  
2. **M080:** propagate exit codes through CLI top-level exception handler.  
3. **M015:** integrate into tool/MCP path (merge with `injection_defense`).  
4. **M081/M082:** help examples + real completion show/install.  
5. **Self-audit Should 100% rows** (S105/S106/S114/S124/S108/S110/S115/S132) for true wiring.  
6. **Land WIP** S104/S109/S112 cleanly.  
7. **Regenerate** improved scorecard honestly; only then move M080/M015/M081/M082 to COMPLETE.

---

## 10. What Grok already finished (context only)

Memory roadmap **P1–P8** on master (do not reimplement):

| Phase | Tip (approx) | Surface |
|-------|----------------|---------|
| P1 KG | `5f2fe23` | `superai kg` |
| P2 Cognify | `61c0e55` | `superai cognify` |
| P3 Session | `b37e65e` | `superai memory-session` |
| P4 Recall | `39d2a52` | `superai recall` |
| P5 Ingest | `e35536b` | `superai ingest` |
| P6 Ontology | `a754236` | `superai ontology` |
| P7 Datasets | `dc6fef4` | `superai dataset` |
| P8 Capture | `144bba5` | `superai capture` |

---

## 11. Quick checklist for AGY (print / tick)

- [ ] CLI commands registered and on `--help`  
- [ ] `test_cli_help_and_completion_m081_m082.py` green  
- [ ] M080 exits used at CLI boundary  
- [ ] M015 invoked on real tool/MCP untrusted data  
- [ ] M015 unified with `injection_defense`  
- [ ] M081 examples improved  
- [ ] M082 completion show/install works on Win PS + bash  
- [ ] S116 CLI optional polish  
- [ ] Shoulds re-validated (not paper 100%)  
- [ ] Uncommitted S104/S109/S112 finished or discarded intentionally  
- [ ] Scorecard regenerated; commit messages match  
- [ ] Memory P1–P8 tests still green after your changes  

---

*End of handoff. Questions: coordinate on `main.py` / `mcp_server.py` only; memory modules stay Grok unless explicitly shared.*
