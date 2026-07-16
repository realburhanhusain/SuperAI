# MoSCoW 100% plan — honest tracking

**Updated:** 2026-07-16  
**Policy:** An item is `[x]` only when code exists **and** unit tests pass for it.  
**Prior “sprint complete”** = vertical slice, **not** full MoSCoW. This file is the truth.

**Verification evidence (this pass):**
```text
pytest tests/test_moscow_100.py tests/test_path_which.py tests/test_result_contract.py tests/test_improvement_v3.py -q
# 34 passed

pytest -m unit -q
# 34 passed, 283 deselected
```

**Not claimed:** Live multi-vendor smoke with real API keys (N8 / Phase 99) — harness only.

## Must

| ID | Item | DoD | Status |
|----|------|-----|--------|
| M1 | Model tool protocol | `tool_protocol` + tests | **[x]** |
| M2 | Failover + fail-closed | readiness + multi-model try | **[x]** |
| M3 | Cost on workers | cost_router in orchestrator/board | **[x]** |
| M4 | Tenant R/W everywhere memory | write_back + query tags + scope + export/import | **[x]** |
| M5 | Diff check/apply | `git_diff_apply` check + apply | **[x]** |
| M6 | Contract on all major public APIs | council, compare, cli-run, pr_review, web `/api/status` | **[x]** |
| M7 | Goals execute safe | caps + no yolo | **[x]** |
| M8 | pytest -m unit | markers + suite | **[x]** |

## Should

| ID | Item | Status |
|----|------|--------|
| S1 | Token streaming in agent-tui | **[x]** `token_stream` + Live panel |
| S2 | Live vision call path | **[x]** `vision_attachments` through `ModelCaller` + `call_with_images` |
| S3 | Semantic board cache | **[x]** `semantic_subject_key` + `SUPERAI_BOARD_SEMANTIC` |
| S4 | Worker diversity 1 premium + N cheap | **[x]** `diversify_pool` / `resolve_worker_pool` |
| S5 | Bakeoff bandit pin | **[x]** |
| S6 | Graph SVG UI | **[x]** |
| S7 | Shared ask session MCP/TUI | **[x]** shared root + MCP `superai_ask_session` |
| S8 | Side-effect audit | **[x]** |
| S9 | NL for goals/bakeoff/agent-tui/profile | **[x]** dedicated actions + handlers |
| S10 | Windows path_which tests | **[x]** expanded tests |

## Nice

| ID | Item | Status |
|----|------|--------|
| N1 | Richer agent TUI (panels, /diff confirm) | **[x]** `/panel` `/diff` `/stream` |
| N2 | Assistant daemon tick + schedule goals | **[x]** `daemon_tick` + `goals tick` CLI |
| N3 | Worktree subagent runner | **[x]** `worktree_subagent` + `worktree-run` CLI |
| N4 | Bakeoff report file + eval hook | **[x]** report path + `default_eval_hook` |
| N5 | Plugin catalog verify-sha default path | **[x]** `~/.superai/plugin_sha` |
| N6 | Voice hooks in agent-tui | **[x]** `/listen` `/speak` → `voice_io` |
| N7 | Team palace export/import by tenant | **[x]** `tenant-export` / `tenant-import` |
| N8 | Live multi-vendor smoke | **POSTPONED** — `smoke_harness` only (never false pass) |

## Not important / explicit non-goals

| Item | Status |
|------|--------|
| Claiming live smoke passed without keys | **Will not lie** — harness only (`live_passed=False` by default) |
| Full agent rewrite (patterns, not fork) | **[x]** SuperAI multi-agent — `docs/SUPER_AGENT.md` · brand is SuperAI only |

### Not-important polish pack (pre–live smoke)

| ID | Item | Status |
|----|------|--------|
| W1 | Session export markdown | **[x]** |
| W2 | Session list + resume | **[x]** |
| W3 | Undo last turn | **[x]** |
| W4 | Cost/token session totals | **[x]** |
| W5 | Command palette + aliases | **[x]** |
| W6 | Multi-line paste mode | **[x]** |
| W7 | VS Code extension depth | **[x]** |
| W8 | Smoke preflight checklist | **[x]** `superai smoke-preflight` |

**Next external gate only:** Phase 99 live multi-vendor smoke (with real keys).

## Commands

```powershell
# Contracts / boards
superai council "topic"   # contract envelope
superai compare "prompt" -m gpt-4o,deepseek-chat
superai smoke-harness     # N8 inventory only
superai smoke-harness --allow-live   # only if keys present; still honest

# Agent / sessions
superai agent-tui         # /stream /panel /diff /listen /speak
superai goals tick
superai goals execute --max 2
superai bakeoff "hi" -m gpt-4o,deepseek-chat --pin

# Tenant / worktree
superai tenant-export -t team-a
superai tenant-import path.json --dry-run
superai worktree-run "task" --dry-run

# Tests
pytest tests/test_moscow_100.py -q
pytest -m unit -q
```

## Honesty note

If a future agent marks items complete without tests, treat this file’s policy as the override: **code + tests, or not done**.
