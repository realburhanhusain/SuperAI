# AGY Scorecard Hardening Plan — Pending Feature Improvements

**Created:** 2026-07-23  
**Baseline tip:** `b5888e7` + local WIP (Must CLI wiring in progress)  
**Source of truth for gaps:** `docs/AGY_HANDOFF_PENDING_AND_INCOMPLETE.md`  
**Taskboard:** `TASKBOARD.md` → section **AGY Hardening Wave**  
**Strict bar:** code + docs + tests + product wiring (CLI/MCP/hooks where claimed)

---

## 1. Goals

1. Close **P0** Must CLI / integration so M080/M015/M081/M082/S116 meet the strict bar or honest partial %.  
2. Fix **false COMPLETE 100%** Shoulds: wire missing CLIs, real enforcement, parser bugs.  
3. Restore any CLI dropped during WIP (e.g. `check critique`, `check upgrades`).  
4. Regenerate improved scorecard **honestly** only after green verification.  
5. Do **not** break memory roadmap P1–P8 modules.

---

## 2. Workstreams & priority

| Wave | Name | IDs | Effort | Outcome |
|------|------|-----|--------|---------|
| **W0** | Stabilize WIP + restore regressions | CLI, dep_upgrade | 0.5 d | Must CLI green; critique/upgrades restored |
| **W1** | Must product wiring | M080, M015, M081, M082, S116 | 1–2 d | Real exits; injection in tool path; completion/help honest |
| **W2** | Critical Should product gaps | S110, S114, S132, S112, S115, S117 | 1–2 d | CLIs work; budget enforced; parsers honest |
| **W3** | Quality Should harden | S104, S105, S106, S108, S109, S124 | 1–2 d | Less overclaim; bugs fixed; docs match |
| **W4** | Scorecard + handoff closeout | all | 0.5 d | Honest percents; handoff checkboxes |

---

## 3. Detailed tasks

### W0 — Stabilize current WIP

| ID | Task | Acceptance |
|----|------|------------|
| W0.1 | Keep Must CLI: `exit-codes`, `completion show/install`, `git suggest-*`, `prompt-injection scan/wrap` | `test_cli_help_and_completion_m081_m082.py` green |
| W0.2 | Restore `superai check critique` (S104) and `superai check upgrades` (S112) if removed | `check --help` lists both; smoke exit 0 |
| W0.3 | Keep `git explain-pr`, `git resolve-conflicts`, `security scan-secrets`, `ci-fix` | Smoke + unit tests |
| W0.4 | Finish S112 tomllib pyproject path; unit test on SuperAI-shaped fixture | No `"typer` package names; total ≈ real deps |
| W0.5 | Fix `EXIT_CODES_TABLE` display names (OK/BUDGET/… not first word of desc) | `exit-codes` output readable |
| W0.6 | Commit only after W0 tests green | Conventional commit message |

### W1 — Musts

| ID | Task | Acceptance |
|----|------|------------|
| W1.1 **M080** | Wire `from_exception` / `from_result` at CLI top-level exception path where feasible | At least central handler maps budget/validation/jail |
| W1.2 **M080** | Document remaining hard-coded `Exit(1)` as follow-up or convert high-traffic paths | Scorecard can stay <100 if honest |
| W1.3 **M015** | Bridge `prompt_injection` into tool results path (call from `injection_defense` or mcp/agent tools) | At least one production call site + test |
| W1.4 **M015** | Unify API surface (`scan_prompt_injection` aliases OK) | Single recommended import path in docs |
| W1.5 **M081** | Improve help for new groups (examples in help strings) | Spot-check `--help` |
| W1.6 **M082** | Prefer real Typer completion dump if available; else label stub honest in help | Docs match behavior |
| W1.7 **S116** | CLI already under `git suggest-*` — ensure tests stay green | Pass |

### W2 — Critical Should product gaps

| ID | Task | Acceptance |
|----|------|------------|
| W2.1 **S110** | CLI `git explain-pr` (done in WIP) + better base (`main...HEAD` or staged+unstaged) | Docs match; unit/integration smoke |
| W2.2 **S114** | CLI `security scan-secrets` (done in WIP) + optional hook call site (e.g. pre-tool or git helper) | Docs “hooks” honest or real hook |
| W2.3 **S132** | Call `check_command_budget_guard` from `spend_guard.budget_precheck` or CLI expensive cmds | Setting limit actually blocks overspend |
| W2.4 **S112** | Harden tomllib + poetry optional; strip extras markers | Fixture test |
| W2.5 **S115** | Either real license lookup **or** rename docs to “GPL-name heuristic”; fix pyproject counting | No false 100% compliance on empty heuristics |
| W2.6 **S117** | Docs path = `superai git resolve-conflicts`; remove dead imports | Docs match CLI |

### W3 — Quality harden

| ID | Task | Acceptance |
|----|------|------------|
| W3.1 **S108** | Fix method double-count (`ast.walk` vs module body only) | Test asserts single method entry |
| W3.2 **S106** | Flag missing annotations on public defs **or** rename module/docs off “typecheck” | Honest naming |
| W3.3 **S105** | Subprocess pytest optional; tighter stem match (`test_{stem}` exact/prefix) | Less over-match |
| W3.4 **S104** | WARNING fails `passed` when policy=strict; document | Test |
| W3.5 **S109** | Traceback line harvest or drop unused failure types from comments | Docs honest |
| W3.6 **S124** | Drop Java/Node claim or add minimal parsers | Docs honest |

### W4 — Closeout

| ID | Task | Acceptance |
|----|------|------------|
| W4.1 | Update `AGY_HANDOFF_…` checkboxes | Accurate |
| W4.2 | Regenerate improved scorecard only for IDs that truly pass strict bar | No false 100% |
| W4.3 | Memory P1–P8 regression green | 72 tests pass |
| W4.4 | Push plan + commits | `origin/master` |

---

## 4. Non-goals (this wave)

- Full mypy/pyright productization  
- Real SCA/CVE database for S114  
- Full license SPDX API for S115 (unless quick offline map)  
- Live multi-provider smoke (still postponed)  
- Memory P1–P8 redesign  

---

## 5. Verification commands

```powershell
cd C:\Users\burhan.husain\Documents\Personal\github\SuperAI

# Must CLI
python -m pytest tests/test_cli_help_and_completion_m081_m082.py tests/test_exit_codes_m080.py tests/test_prompt_injection_m015.py tests/test_git_helpers_s116.py -q

# Should packs
python -m pytest tests/test_auto_test_runner_s105.py tests/test_lint_typecheck_s106.py tests/test_symbol_nav_s108.py tests/test_pr_explainer_s110.py tests/test_security_scan_s114.py tests/test_license_check_s115.py tests/test_log_triage_s124.py tests/test_command_budget_s132.py tests/test_self_critique_s104.py tests/test_ci_fixer_s109.py tests/test_dep_upgrade_s112.py tests/test_merge_conflict_helper_s117.py -q

# Memory
python -m pytest tests/test_knowledge_graph_p1.py tests/test_cognify_p2.py tests/test_session_memory_p3.py tests/test_recall_router_p4.py tests/test_ingest_p5.py tests/test_ontology_p6.py tests/test_memory_dataset_p7.py tests/test_session_capture_p8.py -q
```

---

## 6. Execution order (implementation)

```text
W0.2 restore critique/upgrades
  → W0.4/W0.5 dep_upgrade + exit table
  → W2.3 S132 spend_guard
  → W3.1 S108 double-count
  → W1.3 M015 tool bridge (minimal)
  → W2.5 S115 honesty (docs + count fix)
  → W3.2 S106 annotation flag or rename
  → W0.6 commit
  → continue W1/W3 remaining
  → W4 scorecard
```

---

## 7. Status snapshot (plan creation)

| Item | Status |
|------|--------|
| Must CLI suite | **Green** on local WIP (8/8) |
| `check critique` / `check upgrades` | **Broken** (exit 2) — restore first |
| S112 tomllib | **Partial** in WIP |
| S110/S114 CLI | **Present** in WIP |
| S132 enforcement | **Not done** |
| Scorecard honesty | **Not regenerated** |
