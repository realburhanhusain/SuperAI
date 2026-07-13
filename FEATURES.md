# SuperAI — Features (aligned with code)

**Repo:** SuperAI_v1 · **Truth board:** `TASKBOARD.md` · **Progress:** `docs/PROGRESS.md`  
Features mark **Implemented** vs **Deferred smoke** (host credentials / admin).

## 1. Multi-model orchestration

| Feature | Status |
|---------|--------|
| Supervisor-style multi-step task plans | **Implemented** |
| Sequential + **parallel** step execution (`depends_on` / `can_run_parallel`) | **Implemented** |
| Structured run results (JSON) + Pydantic `TaskResult` | **Implemented** |
| Mock mode without API keys | **Implemented** |
| Recursive hierarchical delegation (`delegate`) | **Implemented** |

## 2. Routing & resilience

| Feature | Status |
|---------|--------|
| Task classification | **Implemented** |
| Scoring router (task, history, cost, latency, health) | **Implemented** |
| Strategies: smart_fallback, round_robin, latency_based, cost_based | **Implemented** |
| Circuit breaker + retry/backoff | **Implemented** |
| Provider health + quota windows | **Implemented** |
| Contextual bandit blend + reward updates | **Implemented** |
| Live multi-provider smoke harness | **Implemented code** — **Deferred smoke** (keys) |

## 3. Models & discovery

| Feature | Status |
|---------|--------|
| Model registry + refresh | **Implemented** |
| Broad provider call paths | **Implemented** |
| External AI CLI discovery + `cli-run` | **Implemented** |
| MCP-style context packs | **Implemented** |

## 4. Self-learning & memory

| Feature | Status |
|---------|--------|
| Memory Palace + embeddings path | **Implemented** |
| Learn / conflicts / distill / decay | **Implemented** |
| Mid-task memory injection | **Implemented** |
| Wings & rooms + provenance | **Implemented** |
| User preference model | **Implemented** |

## 5. Skills

| Feature | Status |
|---------|--------|
| Markdown skills + inject + auto-create sandbox | **Implemented** |
| Promote / rollback / analytics | **Implemented** |

## 6. Backup & security

| Feature | Status |
|---------|--------|
| AES-GCM + zstd encrypted backups | **Implemented** |
| Incremental + verify + restore | **Implemented** |
| Auto-backup on clean exit | **Implemented** |
| rclone cloud push/pull | **Implemented code** — **Deferred smoke** (rclone remote) |

## 7. CLI, web & UX

| Feature | Status |
|---------|--------|
| Typer CLI + Rich + progress bars | **Implemented** |
| Shell completion | **Implemented** |
| Terminal dashboard (`superai dashboard`) | **Implemented** |
| Web memory + charts + dashboard API | **Implemented** (`pip install -e ".[web]"`) |
| Cross-surface feedback | **Implemented** |

## 8. Advanced / ecosystem

| Feature | Status |
|---------|--------|
| External CLI delegation + approval | **Implemented** |
| Tool proposals | **Implemented** |
| Council voting (majority\|supervisor\|weighted) | **Implemented** |
| Agentic debate / critique | **Implemented** |
| Messengers (cli/file/webhook/telegram/slack) | **Implemented** (live tokens deferred) |
| Databao NL SQL + Vega HTML | **Implemented** |
| Plugin marketplace registry | **Implemented** |
| n8n/Zapier/Make webhooks + search stubs | **Implemented** |
| GitHub Pages workflow | **Implemented** — **Deferred** enable in repo settings |

## Future Plan gap-close (2026-07-14)

| Feature | Status |
|---------|--------|
| Model compare + benchmark | **Implemented** |
| Plan export JSON/Markdown | **Implemented** |
| Step result cache | **Implemented** |
| Parallel voting LB strategy | **Implemented** |
| Model blacklist (auto + manual) | **Implemented** |
| Skill create/delete/improve/deps/test | **Implemented** |
| Selective backup scopes | **Implemented** |
| External CLI dual-register as models | **Implemented** |
| Multi-turn memory chat | **Implemented** |
| Model version pinning | **Implemented** |
| Notion integration (API or dry-run) | **Implemented** |
| HITL clarify / answer / veto | **Implemented** |
| GitHub release + backup workflows | **Implemented** |

See `docs/DOC_GAP_ANALYSIS.md`.

## Deferred (last activity — smoke only)

1. Live provider API keys multi-smoke  
2. Live Telegram/Slack tokens  
3. rclone remote E2E  
4. GitHub Pages admin toggle  
