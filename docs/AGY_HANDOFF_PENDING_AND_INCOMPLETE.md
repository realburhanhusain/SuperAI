# AGY Handoff — Pending & Incomplete Findings

**Author:** Grok (memory roadmap track)  
**First written:** 2026-07-23 (tip `144bba5`)  
**Last re-review:** 2026-07-24 (Hardening Wave closeout by Grok after reassignment)  
**Repo:** `Documents/Personal/github/SuperAI`  
**Audience:** AGY (scorecard / V1–V6 Musts & Shoulds)  
**Strict bar:** production code + thorough docs + full tests **and** product wiring (CLI/MCP/tool paths where claimed)

---

## Re-review log

| When | Tip | What was reviewed |
|------|-----|-------------------|
| 2026-07-23 first | `144bba5` | M080/M015/M081/M082/S116 + Shoulds S105–S132 pack |
| 2026-07-23 **#2** | **`b5888e7`** | **S104 self-critique, S109 CI fixer, S112 dep upgrade, S117 merge conflict** (+ scorecard promotion to 100%) |
| 2026-07-23 **#3 validation** | **`b5888e7`** | Full AGY inventory vs commits/scorecard; CLI wiring matrix; full AGY pytest matrix (**49 pass / 8 fail**) |
| 2026-07-23 **#4 deep 8** | **`b5888e7`** | **Deep review of former medium set:** S105, S106, S108, S110, S114, S115, S124, S132 (code+tests+docs+wiring+edge probes) |
| 2026-07-23 **#5 claim check** | **`eba76f2`** | User claim: AGY completed all pending tasks. **Verdict: NOT fully true** — major P0/P1 CLI + many fixes landed; remaining W1/W3/W4 items still open (see §0d). |
| 2026-07-23 **#6 claim re-check** | **`7695d80`** | User: AGY said all gaps closed again. **Verdict: REJECT** — see §0e. |
| 2026-07-24 **#7 closeout** | (this commit) | User reassigned remaining AGY opens to Grok. **Hardening Wave W1/W3/W4 closed** with honest scorecard demotions — see §0f. |

---

## 0f. Hardening Wave closeout (2026-07-24)

User asked Grok to finish remaining AGY open items (W1.1–W1.2, W1.5–W1.6, W3.3 stem, W3.5, W4).

| Item | Status |
|------|--------|
| W1.1 M080 CLI entry mapping | **DONE** — `scli.main:main` + `from_exception` |
| W1.2 residual Exit(1) honesty | **DONE** — documented migrate-on-touch; not false 100% |
| W1.5 M081 help examples | **DONE** |
| W1.6 M082 completion honesty | **DONE** — Typer env complete; install fail ≠ success |
| W3.3 S105 stem match | **DONE** — prefix/exact, less over-match |
| W3.5 S109 traceback harvest | **DONE** — File/line walkback |
| W4.2 scorecard honesty | **DONE** — M015/M080–082 + thin Shoulds demoted from false 100% |
| Residual | Host-gated live smoke; remaining hard-coded `Exit(1)` paths |

---

## 0e. Re-review #6 — "all gaps closed?" (2026-07-23, tip `7695d80`)

**Claim:** AGY told stakeholders all gaps are closed.  
**Evidence:** `git log` / clean tree at `7695d80`; last AGY code commit is **`8efe54e`** (after `eba76f2` / `8681e6a`); post-`8efe54e` commits are **Grok memory/docs only**; focused AGY unit pack **41 passed**; scorecard + TASKBOARD re-read.

### Verdict

| Scope | Result |
|-------|--------|
| **P0 Must CLI wiring** | **DONE** (still green) |
| **Critical Should product CLIs** (S110/S114/S116/S117 + S132/M015 bridges) | **DONE / mostly DONE** |
| **Quality patches in `8efe54e`** | **Partial credit** — S104 strict + S109 SYNTAX/TIMEOUT + completion install Path fix |
| **Full Hardening Wave W0–W4** | **NOT done** |
| **Musts at strict 100% scorecard** | **NO** — M080/M015/M081/M082 still **Complete? NO** |
| **Honest "all gaps closed"** | **Reject** |

### Done since re-review #5 (credit)

| Area | Evidence at `7695d80` |
|------|------------------------|
| **S104 W3.4 (code)** | `run_self_critique_pass(..., strict=True)` → WARNING fails `passed` (probe: bare `except` → `passed=False`) |
| **S109 W3.5 (partial)** | `ci_fixer` parses TEST_FAILURE / IMPORT_ERROR / **SYNTAX_ERROR** / **TIMEOUT**; better line harvest on FAILED |
| **M082 install** | `completion install` imports `Path`, appends shell profile block (no longer no-op) |
| Unit packs | Should suite sample **41 passed** |

### Still open (not completed)

| ID / task | Status | Evidence |
|-----------|--------|----------|
| **W1.1–W1.2 M080** product-wide exits | **Open** | `from_exception` **0** call sites in `src/cli/main.py`; **~114** `typer.Exit(...)`; only `public_surface` uses `from_result` |
| **M080 quality** | **Open** | **Duplicate** `def from_exception` in `exit_codes.py` (second shadows first); bare `TimeoutError` can map to GENERAL not TIMEOUT |
| **W1.5 M081** help examples | **Open** | Groups exist; no dedicated help-quality pass |
| **W1.6 M082** completion honesty | **Partial** | `show` still env-eval one-liners (not full Typer dump); `install` writes profile; error path can still print success |
| **W3.3 S105** | **Open** | Stem substring match + in-process `pytest.main` |
| **W3.4 S104** | **Code closed** | Implementation done in `8efe54e`; TASKBOARD synced in #6 |
| **W3.5 S109** | **Partial** | Types exist; not a real patch-applier; many `line_number=0` |
| **W4.1** | **Synced by Grok** | Handoff §0e + TASKBOARD #6 note |
| **W4.2** | **Open** | Should rows still **YES/100%** overclaim; Musts honestly **NO** |
| **W0.6 / W4.4** | **Open** | Closeout hygiene / remaining AGY-owned push |

### Improved scorecard (honest Must rows — still incomplete)

| ID | Complete? | % |
|----|-----------|---|
| M080 | **NO** | 80% |
| M015 | **NO** | 70% |
| M081 | **NO** | 60% |
| M082 | **NO** | 55% |

### Test matrix (#6)

```text
AGY Should unit pack (S104–S132 sample files): 41 passed
```

### Bottom line for stakeholders

AGY **finished the wiring wave** and some **quality patches**. Residual Hardening Wave work remains on **product-wide exits, help/completion depth, S105, scorecard honesty, and taskboard closeout**.

**Grok will not implement AGY-owned opens** unless reassigned. Memory residual backlog (MR-1…) is the disjoint Grok track.


---

## 0d. Re-review #5 — “all pending tasks completed?” (2026-07-23, tip `eba76f2`)

**Claim:** AGY completed all pending tasks identified earlier.  
**Evidence:** tip `eba76f2` / `8681e6a` (no newer AGY “closeout” commit after plan); full AGY pytest matrix **59 passed**; code re-read of open items.

### Verdict

| Scope | Result |
|-------|--------|
| **P0 Must CLI wiring** (originally the biggest gap) | **DONE** — suite green |
| **Critical Should product gaps** (S110/S114 CLI, S112, S132, S115, S117) | **Mostly DONE** |
| **All hardening-wave tasks (W0–W4)** | **NOT done** |
| **Musts at strict 100% scorecard** | **NO** — M080/M015/M081/M082 still **Complete? NO** in improved scorecard |
| **Honest “all pending closed”** | **Reject** |

### Done since original handoff (credit)

| Area | Evidence |
|------|----------|
| Must CLI | `exit-codes`, `completion`, `git suggest-*`, `prompt-injection scan/wrap` — **8/8 CLI tests pass** |
| S110 | `superai git explain-pr` |
| S114 | `superai security scan-secrets` |
| S116 | `superai git suggest-branch/commit` |
| S117 | `superai git resolve-conflicts` |
| S112 | tomllib pyproject path + tests |
| S108 | method double-count fixed |
| S106 | ANN001/ANN201 annotation checks |
| S132 | `spend_guard.budget_precheck` calls `check_command_budget_guard` |
| M015 | `injection_defense.sanitize_tool_result` calls `prompt_injection` |
| S124 | Java/Node claim removed from module doc |
| S115 | pyproject count + heuristic honesty messages |

### Still open (not completed)

| ID / task | Status | Evidence |
|-----------|--------|----------|
| **W1.1–W1.2 M080** product-wide exits | **Open** | CLI lists codes; no top-level `from_exception` wiring; many `typer.Exit(1)` remain |
| **W1.5 M081** help examples | **Open** | Groups exist; no dedicated help-quality pass |
| **W1.6 M082** completion honesty | **Open** | `completion show` prints a **stub** one-liner, not a real script; `install` claims success without writing shell config |
| **W3.3 S105** tighter impact + subprocess | **Open** | Still stem substring + in-process `pytest.main` |
| **W3.4 S104** WARNING fails `passed` | **Open** | `passed = not has_errors` — WARNING/INFO still pass |
| **W3.5 S109** traceback lines / SYNTAX/TIMEOUT | **Open** | Only FAILED + ModuleNotFoundError; `line_number=0` always for those |
| **W4.2** Honest scorecard regen | **Open** | M080/M015/M081/M082 still NO; Shoulds still many at 100% overclaim |
| **W4.1** Handoff checkboxes | **Open** | Taskboard still has open `[ ]` for W1/W3/W4 |

### Test matrix (#5)

```text
AGY unit + Must CLI: 59 passed
```

### Bottom line for stakeholders

AGY (with Grok assist on the hardening commit) **closed the original P0 “CLI never wired” crisis** and most **product-wiring** gaps for Shoulds. That is real progress.

It has **not** finished every task on the AGY Hardening Wave plan. Treating scorecard Musts as complete or claiming “all pending done” would be **incorrect**.

---


## 0c. Deep review — former “medium 8” (S105 / S106 / S108 / S110 / S114 / S115 / S124 / S132)

**Unit pack re-run:** `25 passed` for these eight test files.  
**Scorecard:** all eight marked **Complete? YES / 100%** — **overstated** under strict bar in every case below.

### S105 — Auto test discovery / impacted runner

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/auto_test_runner.py` |
| Docs | `docs/AUTO_TEST_RUNNER.md` |
| Tests | `tests/test_auto_test_runner_s105.py` (4) — **pass** |
| CLI | **`superai test impacted <files...>`** — wired |

**Behavior**
- Maps modified paths → `tests/test_*` by **filename stem substring** (`stem in t_stem` or `startswith`).
- `run_impacted_tests` calls **`pytest.main([...])` in-process**.

**Bugs / gaps**
- [ ] Matching is crude: short stems (`config`, `errors`, `main`) can over-select or under-select unrelated suites.
- [ ] No import-graph / coverage / git-diff analysis — not “impact analysis”, name oversells.
- [ ] In-process `pytest.main` pollutes process, can conflict with outer pytest, no timeout/isolation.
- [ ] No post-edit hook (editor/agent) — opt-in CLI only.
- [ ] Return payload omits `message` on failure path sometimes expected by CLI.

**Strict %:** ~**55–65%**. Do **not** treat as 100% complete impact runner.

---

### S106 — Lint / typecheck post-edit

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/lint_typecheck.py` |
| Docs | `docs/LINT_TYPECHECK.md` |
| Tests | `tests/test_lint_typecheck_s106.py` (4) — **pass** |
| CLI | **`superai check lint <files...>`** — wired |

**Behavior**
- `ast.parse` for syntax; walk for **bare `except:`** only.
- Comment/doc claim “type verification” — **no annotation checks implemented**.

**Bugs / gaps**
- [ ] **Not a typechecker** (no mypy/pyright); name and scorecard claim overstate.
- [ ] No flake8/ruff/pylint integration.
- [ ] Comment says “missing type annotations on defs” but code never flags them.
- [ ] Non-Python files not handled gracefully (parse may fail or skip poorly).

**Strict %:** ~**50–60%** (syntax + bare-except only).

---

### S108 — Symbol-aware navigation

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/symbol_nav.py` |
| Docs | `docs/SYMBOL_NAV.md` |
| Tests | `tests/test_symbol_nav_s108.py` (2) — **pass** (weak asserts) |
| CLI | **`superai symbol search <query>`** — wired |

**Behavior**
- AST index of classes/functions/methods under `src/` (or cwd).
- Substring match on symbol name.

**Bugs / gaps**
- [ ] **`ast.walk` double-counts methods:** class methods are added as `method` **and** again as top-level `function` (elif branch runs for nested FunctionDef nodes).
- [ ] No variables/constants despite kind enum comment.
- [ ] No go-to-def, references, or cross-file call graph — “beyond grep” is only AST name index + substring.
- [ ] Full-tree `rglob` every search — no cache; slow on large trees.
- [ ] Tests never assert method kind or absence of duplicates.

**Strict %:** ~**55–65%**.

---

### S110 — PR explainer (file-level findings)

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/pr_explainer.py` |
| Docs | `docs/PR_EXPLAINER.md` claims **`superai git explain-pr`** |
| Tests | `tests/test_pr_explainer_s110.py` (2) — **pass** |
| CLI | **NOT REGISTERED** — only comment + broken `from scli.main import git_app` stub |

**Behavior**
- Parses unified diff for `+/-` counts per file; builds Markdown table.
- `generate_pr_explanation_from_repo` runs `git diff HEAD~1` then staged.

**Bugs / gaps**
- [ ] **No product CLI** despite docs — **scorecard 100% invalid** for “shipped feature”.
- [ ] Findings are **only line counts**, not semantic review findings.
- [ ] `HEAD~1` only — wrong for multi-commit PRs / branch vs main.
- [ ] Dead circular import of `git_app` never attaches command.
- [ ] No gh/GitLab API integration.

**Strict %:** ~**40–50%** library utility; **incomplete product**.

---

### S114 — Security scan hooks (secrets, vulns)

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/security_scan.py` |
| Docs | `docs/SECURITY_SCAN_HOOKS.md` claims **`superai security scan-secrets`** |
| Tests | `tests/test_security_scan_s114.py` (4) — **pass** |
| CLI | **NOT REGISTERED** |
| Hooks | **None** to pre-commit / git / edit pipeline |

**Behavior**
- Regex patterns: OpenAI/Anthropic/AWS keys, private key headers, bearer tokens, generic api_key=.
- Redacts snippets in findings.

**Bugs / gaps**
- [ ] **No CLI, no hooks** — name “hooks” is false advertising.
- [ ] **No vulnerability scanning** (SCA/CVEs) — secrets only.
- [ ] Parallel older path: `foundation_modules.security_scan_text` / `foundation_complete.security_scan` — not unified with this module.
- [ ] False positives/negatives inherent to short regex set (no entropy, no allowlist).
- [ ] Missing file → empty “no secrets” (silent false clean).

**Strict %:** ~**40–50%** (regex library only).

---

### S115 — License / compliance on new deps

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/license_check.py` |
| Docs | `docs/LICENSE_COMPLIANCE.md` |
| Tests | `tests/test_license_check_s115.py` (3) — **pass** (heuristic only) |
| CLI | **`superai check license <manifest>`** — wired |

**Behavior**
- Flags packages **if package name or line contains `gpl`/`agpl` string**.
- `PERMISSIVE_LICENSES` / `COPYLEFT_LICENSES` sets are **defined but never used**.

**Bugs / gaps**
- [ ] **Does not read license metadata** from PyPI/npm or package METADATA.
- [ ] MIT/Apache packages never inspected — “compliant” means “name didn’t contain gpl”.
- [ ] **pyproject.toml line counting** same class of bug as S112 (`total_packages` ≈ 58 on SuperAI pyproject).
- [ ] package.json heuristic flags package **names** containing gpl, not licenses field.

**Strict %:** ~**35–45%**. Not a real license compliance tool.

---

### S124 — Log triage / stack traces

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/log_triage.py` |
| Docs | `docs/LOG_TRIAGE.md` |
| Tests | `tests/test_log_triage_s124.py` (3) — **pass** |
| CLI | **`superai triage-log <path|text>`** — wired |

**Behavior**
- Python `File "...", line N, in func` frames + `*Error/*Exception:` lines.
- Template `suggested_fix` by exception type.
- Last frame used as “top” (often correct for Python).

**Bugs / gaps**
- [ ] Docstring claims **Java and Node.js** — **not implemented**.
- [ ] No chained-exception / “During handling of” support.
- [ ] Suggestions are generic boilerplate, not code-aware.
- [ ] Overlaps S109 CI fixer without shared parser.

**Strict %:** ~**60–70%** for Python-only triage.

---

### S132 — Per-command budget overrides

| Pillar | Evidence |
|--------|----------|
| Code | `src/core/command_budget.py` |
| Docs | `docs/COMMAND_BUDGET.md` |
| Tests | `tests/test_command_budget_s132.py` (3) — **pass** (isolated file) |
| CLI | **`superai budget command set <name> <usd>`** — wired |

**Behavior**
- Persists limits in `~/.superai/command_budgets.json`.
- `check_command_budget_guard(name, current_spend)` pure function.

**Bugs / gaps**
- [ ] **`check_command_budget_guard` is never called from `spend_guard` or CLI run paths** (grep: only `set_command_budget` in `main.py`).
- [ ] Setting a limit does **not enforce** anything at runtime.
- [ ] No `budget command get|list` CLI.
- [ ] Silent save failure (`except: pass` on write).

**Strict %:** ~**40–50%** (config store + unit tests only; **not an active guard**).

---

### Summary table — deep 8 after #4

| ID | Unit | CLI | Product effect | Strict % | Scorecard 100%? |
|----|------|-----|----------------|----------|-----------------|
| S105 | Pass | Yes | Runs some tests by stem | 55–65 | Overstated |
| S106 | Pass | Yes | Syntax + bare except | 50–60 | Overstated |
| S108 | Pass | Yes | AST name search | 55–65 | Overstated |
| S110 | Pass | **No** | Library only | 40–50 | **False** |
| S114 | Pass | **No** | Library only | 40–50 | **False** |
| S115 | Pass | Yes | Name-contains-gpl only | 35–45 | **False** |
| S124 | Pass | Yes | Python traceback help | 60–70 | Overstated |
| S132 | Pass | Set only | **Not enforced** | 40–50 | **False** |

**Priority fixes for this set**
1. Wire **S110** CLI (`git explain-pr` or equivalent) or demote scorecard.  
2. Wire **S114** CLI + real hook (pre-commit/MCP) or demote.  
3. Call **S132** guard from `spend_guard` / expensive commands.  
4. Fix **S115** to use real license data (or rename to “gpl-name heuristic”).  
5. Fix **S108** method double-count; fix **S106** naming vs typecheck.  
6. Harden **S105** matching + subprocess pytest.

---

## 0b. Coverage validation — have all AGY features been reviewed?

### Inventory of AGY “completed” scorecard IDs (17 total)

| ID | Module present | Unit tests | CLI / product wiring | Review depth | Verdict |
|----|----------------|------------|----------------------|--------------|---------|
| **M015** | `prompt_injection.py` | Pass | **CLI missing**; not in tool loops | **Deep** | Incomplete |
| **M080** | `exit_codes.py` | Pass | Partial (`public_surface` only); **CLI missing** | **Deep** | Incomplete |
| **M081** | (Typer help + docs) | CLI suite **fail** | No dedicated help quality surface | **Deep** | Incomplete |
| **M082** | `add_completion=True` | CLI suite **fail** | No `completion show/install` | **Deep** | Incomplete |
| **S104** | `self_critique.py` | Pass | `superai check critique` | **Deep** | Partial (~65–75%) |
| **S105** | `auto_test_runner.py` | Pass | `superai test impacted` | **Deep (#4)** | Partial (~55–65%); stem match crude |
| **S106** | `lint_typecheck.py` | Pass | `superai check lint` | **Deep (#4)** | Partial (~50–60%); not typecheck |
| **S108** | `symbol_nav.py` | Pass | `superai symbol search` | **Deep (#4)** | Partial (~55–65%); method double-count |
| **S109** | `ci_fixer.py` | Pass | `superai ci-fix` | **Deep** | Partial (~60–70%) |
| **S110** | `pr_explainer.py` | Pass | **CLI NOT wired** | **Deep (#4)** | ~40–50%; 100% false |
| **S112** | `dep_upgrade.py` | Pass | `superai check upgrades` | **Deep** | Partial (~50–60%); pyproject bug |
| **S114** | `security_scan.py` | Pass | **CLI NOT wired** | **Deep (#4)** | ~40–50%; no hooks/vulns |
| **S115** | `license_check.py` | Pass | `superai check license` | **Deep (#4)** | ~35–45%; gpl-name only |
| **S116** | `git_helpers.py` | Pass | **CLI missing** vs tests | **Deep** | Library OK; CLI incomplete |
| **S117** | `merge_conflict_helper.py` | Pass | `superai git-resolve-conflicts` | **Deep** | Partial (~65–75%) |
| **S124** | `log_triage.py` | Pass | `superai triage-log` | **Deep (#4)** | ~60–70%; Python-only |
| **S132** | `command_budget.py` | Pass | set only; **not in spend_guard** | **Deep (#4)** | ~40–50%; no enforcement |

### Commits that define “AGY completed features”

| Commit | IDs |
|--------|-----|
| `07b67ac` | M080, M081, M082, M015, S116 |
| `f0299f5` | scorecard (S116 → COMPLETE only) |
| `73a8751` | S105, S106, S114, S124 |
| `6ac9f5d` | S108, S110, S115, S132 |
| `b5888e7` | S104, S109, S112, S117 |

### Honest answer on review completeness

| Question | Answer |
|----------|--------|
| Are all **17** AGY scorecard IDs **accounted for** in this handoff? | **Yes** |
| Was every ID given **deep code review**? | **Yes (as of #4)** |
| Deep set | All 17: Musts + S104–S132 packs above |
| Full AGY unit matrix (ex-Must CLI) | Green for these Should packs; Must CLI suite still **8 fail** |
| Features outside these 17? | No |

### Bottom line

- **Inventory + deep review:** complete for all AGY-claimed IDs.  
- **Musts:** deep reviewed → still **incomplete** (CLI red).  
- **All Shoulds:** deep reviewed → **none honestly at 100%** under strict bar; worst product gaps **S110/S114 (no CLI), S115 (fake license check), S132 (no enforcement)**.

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

Musts + Should modules (exit_codes, prompt_injection, git_helpers, auto_test_runner, lint_typecheck, security_scan, log_triage, symbol_nav, pr_explainer, license_check, command_budget, **self_critique, ci_fixer, dep_upgrade, merge_conflict_helper**, …) and related docs/tests/scorecard.

### Shared caution

- `src/cli/main.py` and `src/core/mcp_server.py` are **shared**. Prefer additive commands only; re-read before editing; avoid deleting memory commands.  
- History: `0bba3bc` stripped unfinished AGY CLI; `07b67ac` landed Must modules **without** re-wiring Must CLI commands.  
- `b5888e7` correctly **did** wire new Should CLIs (good pattern — apply same to Musts).

---

## 2. Executive summary (updated after `b5888e7`)

### Still open / incomplete (priority order)

| Pri | ID / theme | Status after re-review | Blocker / residual |
|-----|------------|------------------------|--------------------|
| **P0** | CLI for **M080 / M081 / M082 / M015 / S116** | **Still broken** | Commands not registered; **8/8** CLI integration tests fail |
| **P0** | `test_cli_help_and_completion_m081_m082.py` | **RED** | Expects `exit-codes`, `completion`, `git suggest-*`, `prompt-injection` |
| **P1** | **M080** exit codes product-wide | **Partial ~80%** | Library + `public_surface` only |
| **P1** | **M015** tool-loop injection defense | **Partial ~60–70%** | Not wired into tools; duplicates `injection_defense.py` |
| **P1** | **M081 / M082** help & completion | **Not closed** | Docs/tests without working CLI surface |
| **P2** | Scorecard **100%** on new Shoulds | **Overstated** | S104/S109/S112/S117 unit+CLI thin; quality gaps below |
| **P2** | S117 CLI vs docs | **Mismatch** | Docs: `superai git resolve-conflicts`; actual: `superai git-resolve-conflicts` |
| **P2** | S112 pyproject parsing | **Buggy** | Counts non-deps; strips package names with quotes (`"typer`) |
| **P3** | Earlier Shoulds (S105/S106/S114/…) | **Re-audit** | Still often library-first 100% claims |

### Newly landed on master (`b5888e7`) — verdict under strict bar

| ID | Claimed | Unit tests | CLI wired | Strict verdict | Notes |
|----|---------|------------|-----------|----------------|-------|
| **S104** Self-critique | COMPLETE 100% | **Pass** (2) | **Yes** `superai check critique` | **Partial ~65–75%** | Thin AST checks; WARNINGs don’t fail `passed`; not a real DoD gate |
| **S109** CI fixer | COMPLETE 100% | **Pass** (3) | **Yes** `superai ci-fix` | **Partial ~60–70%** | Parse+advice only; no SYNTAX/TIMEOUT paths; no real patches |
| **S112** Dep upgrade | COMPLETE 100% | **Pass** (2) | **Yes** `superai check upgrades` | **Partial ~50–60%** | pyproject parser broken/noisy; no registry/version lookup |
| **S117** Merge conflicts | COMPLETE 100% | **Pass** (2) | **Yes** (standalone cmd) | **Partial ~65–75%** | Marker parse OK; no auto-resolve; docs CLI path wrong; dead `subprocess` import |

**Memory track (Grok):** P1–P8 still done through `144bba5` — not AGY work.

---

## 2b. Thorough review — batch `b5888e7` (S104 / S109 / S112 / S117)

**Commit:** `b5888e7 feat(should): close S104 self critique, S109 ci fixer, S112 dep upgrade assistant, S117 merge conflict helper`  
**Evidence run:** unit tests **9/9 pass**; CLI smoke **exit 0** for `check critique`, `check upgrades`, `ci-fix`, `git-resolve-conflicts`; prior Must CLI suite **still 8 failed**.

### S104 — Self-critique (`src/core/self_critique.py`)

**What works**
- Module docstring + public-fn docstring + bare-`except` AST walk.
- Score = `100 - 5*findings` (floor 0).
- CLI: `superai check critique <file.py>` under existing `check` group.
- Docs: `docs/SELF_CRITIQUE.md`.
- Unit tests cover clean file + missing docstring findings.

**Incomplete / risks**
- [ ] `passed` is only false on **ERROR** severity — missing docs are WARNING/INFO so `passed=True` even with findings (easy false “critique passed”).
- [ ] No type-annotation checks despite TYPE_SAFETY category reserved in comments.
- [ ] No integration into “claim done” / stop hooks / PR flow — opt-in CLI only.
- [ ] Scorecard **100%** overstates production DoD gate.
- [ ] Tests do not assert failure mode for bare except or score math.

**Recommended next**
1. Fail `passed` on WARNING if policy is “before claiming done”.  
2. Add type-hint / complexity checks or rename to “docstring+except lint”.  
3. Optional: call from capture/agent end or pre-commit.

---

### S109 — CI fixer (`src/core/ci_fixer.py`)

**What works**
- Detects pytest `FAILED path::test - msg` and `ModuleNotFoundError`.
- File or paste path auto-detect in CLI `superai ci-fix`.
- Docs + unit tests for clean / failed / import-error logs.

**Incomplete / risks**
- [ ] Dataclass comments list `SYNTAX_ERROR | TIMEOUT` but **no detectors** implemented.
- [ ] “Fixer” only emits **text recommendations** — does not open files, apply patches, or re-run tests.
- [ ] No GitHub Actions / JUnit / generic compiler patterns.
- [ ] line_number always `0` for pytest failures (no traceback line harvest).
- [ ] Scorecard 100% overstates “fix CI failure”.

**Recommended next**
1. Parse traceback frames for line numbers (reuse ideas from S124 log_triage).  
2. Add syntax/timeout detectors or drop from type enum.  
3. Optional: emit structured JSON + optional `--apply` stub (still honest if dry-run only).

---

### S112 — Dependency upgrade assistant (`src/core/dep_upgrade.py`)

**What works**
- package.json `^`/`~`/`*` risk tagging.
- requirements-style `>=` / `==` lines get recommendations.
- CLI: `superai check upgrades <manifest>`.
- Unit tests on temp requirements.txt + package.json.

**Incomplete / risks (important)**
- [ ] **pyproject.toml parsing is incorrect** (live smoke on repo `pyproject.toml`):  
  - `total_dependencies` inflated (e.g. **58**).  
  - Package names broken: `'"typer'`, `'"rich'` (quotes kept).  
  - Spurious entries like `requires-python`.  
- [ ] No comparison to latest PyPI/npm versions — only static constraint heuristics.  
- [ ] Recommends `pip install --upgrade` for **every** pinned/`>=` line including already-pinned — noisy.  
- [ ] No PEP 621 `[project] dependencies = [` array parsing.

**Recommended next**
1. Parse TOML properly (`tomllib` / list entries under `project.dependencies`).  
2. Strip quotes; skip non-package keys.  
3. Optional: query package indexes for real upgrade candidates.  
4. Add unit test on a **fixture pyproject.toml** matching SuperAI shape.  
5. Lower scorecard % until pyproject path is correct (SuperAI’s primary manifest).

---

### S117 — Merge conflict helper (`src/core/merge_conflict_helper.py`)

**What works**
- Solid marker state machine for `<<<<<<<` / `=======` / `>>>>>>>`.
- Extracts ours/theirs content + branch labels.
- Unit tests with sample conflict block.
- CLI registered: `superai git-resolve-conflicts <file>`.

**Incomplete / risks**
- [ ] **Docs lie about CLI:** `docs/MERGE_CONFLICT_HELPER.md` says `superai git resolve-conflicts`; actual command is **`superai git-resolve-conflicts`** (hyphenated top-level, not under `git` group).  
- [ ] Dead code: `import subprocess` unused; circular `from scli.main import git_app` block does nothing useful.  
- [ ] No multi-file `git status` scan; no apply-ours/theirs; no 3-way merge assist.  
- [ ] Recommendation text is generic (“review or union merge”).

**Recommended next**
1. Fix docs CLI path **or** nest under real `git` Typer group as `git resolve-conflicts`.  
2. Remove dead imports.  
3. Optional: `superai git-resolve-conflicts --scan-repo` using `git diff --name-only --diff-filter=U`.

---

### Scorecard honesty on this batch

| Observation | Detail |
|-------------|--------|
| Commit claims “close” S104/S109/S112/S117 | Modules+docs+unit+CLI exist |
| Improved scorecard | All four marked **Complete? YES / 100%** |
| Strict bar | Should be **partial** until S112 parser fixed, S117 docs match, and “fixer/critique” claims match depth |
| Pattern | Same as earlier Should packs: **library + thin unit + mark 100%** |

---

## 3. Critical finding — Must CLI still never re-wired (P0) — **UNCHANGED**

### Evidence (re-verified at `b5888e7`)

```text
python -m pytest tests/test_cli_help_and_completion_m081_m082.py -q
# 8 failed, 0 passed in that file
```

Still missing from Typer app:

```text
superai exit-codes
superai completion show|install
superai git suggest-branch|suggest-commit
superai prompt-injection scan|wrap
```

**Note:** AGY successfully wired **new** Should CLIs in `b5888e7`. Apply the **same discipline** to Musts (highest ROI).

### Required fix

1. Register Must CLI commands on `scli.main:app`.  
2. Ensure `--help` lists them.  
3. Green: `pytest tests/test_cli_help_and_completion_m081_m082.py -q`.

---

## 4. Per-ID findings (landed Musts) — still pending

### M080 — Exit codes — **still incomplete**

| Pillar | Status |
|--------|--------|
| Code | Yes — `exit_codes.py` |
| Docs | Yes — `EXIT_CODES.md` |
| Unit tests | Pass |
| Product wiring | Partial — `public_surface` only |
| CLI list | **Missing** |
| Scorecard | Complete? **NO** ~80% (honest) |

**Pending:** CLI command; map exits at CLI exception boundary; avoid hard-coded `Exit(1)` everywhere.

---

### M015 — Prompt injection — **still incomplete**

| Pillar | Status |
|--------|--------|
| Library | Yes — `prompt_injection.py` |
| Docs | Yes — `PROMPT_INJECTION_DEFENSE.md` |
| Unit tests | Pass |
| Tool-loop wiring | **No** |
| Overlap | `injection_defense.py` still separate |
| CLI | **Missing** |
| Scorecard | Complete? **NO** ~70% |

**Pending:** Unify with `injection_defense`; call from MCP/agent tools; wire CLI or drop tests.

---

### M081 / M082 — Help & completion — **still incomplete**

- Dedicated quality work not evidenced.  
- CLI suite red.  
- Scorecard Complete? **NO**.

---

### S116 — Git helpers — library OK, CLI still missing

- Unit tests pass; scorecard YES 100%.  
- CLI still expected by failing suite.

---

## 5. Scorecard process issues

| Observation | Detail |
|-------------|--------|
| Must commits overclaim | Messages say “close” while scorecard correctly keeps M080/M015/M081/M082 incomplete |
| Should commits overclaim | **100%** for thin helpers (S104/S109/S112/S117 and earlier packs) |
| Generator edits | Hand + script updates both COMPLETE counts and individual rows — keep consistent |

**Pending**
- [ ] Don’t mark 100% until pyproject path (S112) works on this repo.  
- [ ] Align docs CLI names with real commands.  
- [ ] Prefer “library complete / integration partial” language when accurate.

---

## 6. Earlier Should packs (updated after validation #3)

| ID | CLI / wiring (verified) | Residual risks |
|----|-------------------------|----------------|
| S105 auto_test_runner | `superai test impacted` **yes** | Stem heuristics; heavy `pytest.main` |
| S106 lint_typecheck | `superai check lint` **yes** | Not mypy; AST-only |
| S108 symbol_nav | `superai symbol search` **yes** | AST name index vs “beyond grep” claim |
| **S110 pr_explainer** | **NO CLI** — docs say `superai git explain-pr`; only dead `git_app` import | Wire CLI or fix docs; 100% scorecard unjustified |
| **S114 security_scan** | **NO CLI** — docs say `superai security scan-secrets` | Not hooked to pre-commit/edit; 100% unjustified |
| S115 license_check | `superai check license` **yes** | Manifest heuristics only; may not map real licenses |
| S124 log_triage | `superai triage-log` **yes** | Python-centric; template fixes |
| **S132 command_budget** | `superai budget command set` **yes** | **`check_command_budget_guard` not used by `spend_guard`** — set-only product |

---

## 7. Uncommitted WIP

**Cleared at re-review:** S104/S109/S112 previously listed as uncommitted are now on **`b5888e7`**.  
No additional AGY WIP detected in working tree at re-review time (clean `master...origin/master`).

---

## 8. Verification commands

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI

# New batch unit tests (should be green)
python -m pytest tests/test_self_critique_s104.py tests/test_ci_fixer_s109.py tests/test_dep_upgrade_s112.py tests/test_merge_conflict_helper_s117.py -q

# Must CLI integration (currently RED)
python -m pytest tests/test_cli_help_and_completion_m081_m082.py -q --tb=short

# New CLI smoke
python -c "from typer.testing import CliRunner; from scli.main import app; r=CliRunner(); print(r.invoke(app,['check','critique','src/core/exit_codes.py']).exit_code); print(r.invoke(app,['ci-fix','no failures']).exit_code)"

# S112 honesty check on real manifest
python -c "from core.dep_upgrade import check_upgradable_dependencies as c; r=c('pyproject.toml'); print(r.total_dependencies, [x.package_name for x in r.recommendations[:8]])"

# Memory track must stay green
python -m pytest tests/test_knowledge_graph_p1.py tests/test_cognify_p2.py tests/test_session_memory_p3.py tests/test_recall_router_p4.py tests/test_ingest_p5.py tests/test_ontology_p6.py tests/test_memory_dataset_p7.py tests/test_session_capture_p8.py -q
```

---

## 9. Recommended AGY work order (updated)

1. **P0:** Wire Must CLI (`exit-codes`, `completion`, `git suggest-*`, `prompt-injection`) → green M081 suite.  
2. **P0/P1:** Fix **S112** pyproject parsing (repo’s primary manifest).  
3. **P1:** Fix **S117** docs CLI name; remove dead imports.  
4. **P1:** M080 CLI exits + M015 tool-loop integration.  
5. **P2:** Tighten S104 pass criteria; deepen S109 parsers or rename “fixer”.  
6. **P2:** Re-audit older Should 100% rows for real hooks.  
7. **Regenerate** scorecard with honest percents (suggest S112 ≤60 until fixed).

---

## 10. What Grok finished (context)

Memory roadmap **P1–P8** on master (`144bba5` P8). AGY tip **`b5888e7`** is ahead with Should batch only.

---

## 11. Checklist for AGY (print / tick)

### Still open from first review
- [ ] CLI commands registered for Musts and on `--help`  
- [ ] `test_cli_help_and_completion_m081_m082.py` green  
- [ ] M080 exits used at CLI boundary  
- [ ] M015 invoked on real tool/MCP untrusted data  
- [ ] M015 unified with `injection_defense`  
- [ ] M081 examples improved  
- [ ] M082 completion show/install works  
- [ ] S116 CLI optional polish  
- [ ] Older Shoulds re-validated  

### New from re-review `b5888e7`
- [ ] S112: correct PEP 621 / SuperAI `pyproject.toml` parsing  
- [ ] S112: unit test with realistic pyproject fixture  
- [ ] S117: docs CLI matches `git-resolve-conflicts` (or nest under `git`)  
- [ ] S117: remove unused `subprocess` / noop git_app import  
- [ ] S104: decide if WARNING should fail `passed`  
- [ ] S109: implement or drop SYNTAX/TIMEOUT types; optional traceback lines  
- [ ] Scorecard: lower % or annotate residual gaps for S104/S109/S112/S117  
- [ ] Memory P1–P8 tests still green after next AGY commit  

---

*End of handoff (re-review #2 at `b5888e7`).*
