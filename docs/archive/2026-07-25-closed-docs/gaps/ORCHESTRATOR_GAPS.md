# Orchestrator gaps — closed

**Updated:** 2026-07-14  
**Module:** `src/core/orchestrator.py`

## Previously identified gaps → status

| Gap | Status |
|-----|--------|
| No replan after step failure | **Closed** — `_replan_after_failure` + `max_replans` |
| No step retry / failover | **Closed** — retries + `failover_chain` / router candidates + `error_recovery.classify_error` |
| Memory/skills only once at start | **Closed** — `_refresh_enrichment` initial + after each success |
| No quality gate | **Closed** — `_quality_ok` + one rework pass |
| Deadlock on bad deps | **Closed** — dep soft-repair + `dep_repair` events |
| Budget only pre-check | **Closed** — mid-run budget check per step |
| `error_recovery` unused | **Closed** — wired into step attempts |
| Central memory not used in `run` | **Closed** — preface inject + `write_back` after run |
| Silent `except: pass` | **Closed** — `_soft` → `metadata.degraded` + warning logs |
| Parallel context races | **Closed** — `_exec_lock` for context/tokens/cost |
| No adaptation audit trail | **Closed** — `metadata.adaptation_events` |

## Config knobs

| Key | Default | Meaning |
|-----|---------|---------|
| `adapt_on_failure` | `true` | Enable retry / failover / replan |
| `max_step_retries` | `2` | Retries per model when error is retryable |
| `max_replans` | `1` | Recovery plans after hard failures |
| `quality_gate` | `true` | Reject empty/error-like step outputs |
| `mid_task_memory_refresh` | `true` | Refresh Memory Palace after each success |
| `step_retry_backoff_sec` | `0.05` | Backoff between retries |
| `failover_chain` | `[]` | Preferred model order for failover |

## Result metadata

- `metadata.degraded` — optional features that soft-failed  
- `metadata.adaptation_events` — retry / failover / replan / quality / dep_repair  
- `metadata.replans_used` — count of recovery plans  
- `metadata.execution.dep_repairs` — dependency graph repairs  

## Follow-ups (now implemented)

| Feature | How |
|---------|-----|
| HITL replan approval | `replan_requires_approval` / `--replan-approval` → `hitl answer <id> approve` → `--resume` |
| Critic modes | `critic_mode`: `off` \| `light` \| `council` / `--critic` |
| Multi-CLI from run | `run --with-clis claude,aider` (`--cli-live` / `--cli-approve`) |

## Config additions

| Key | Default |
|-----|---------|
| `replan_requires_approval` | `false` |
| `critic_mode` | `light` |
| `council_max_per_run` | `1` |
