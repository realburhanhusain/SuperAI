# SuperAI — Features (aligned with code)

**Repo:** SuperAI_v1 · **Truth board:** `TASKBOARD.md` · **Progress:** `docs/PROGRESS.md`  
Features below mark **Implemented** vs **In progress / planned (required, not optional)**.

## 1. Multi-model orchestration

| Feature | Status |
|---------|--------|
| Supervisor-style multi-step task plans | **Implemented** (`TaskPlanner` + `SuperAIOrchestrator`) |
| Sequential step execution with context handoff | **Implemented** |
| Structured run results (JSON) + history | **Implemented** |
| Mock mode without API keys | **Implemented** |
| Parallel multi-worker execution | **Planned** (Track H) |
| Recursive hierarchical delegation | **Planned** (Track I) |

## 2. Routing & resilience

| Feature | Status |
|---------|--------|
| Task classification (coding/reasoning/research/…) | **Implemented** |
| Scoring router (task match, history, cost, latency, health) | **Implemented** |
| Strategies: smart_fallback, round_robin, latency_based, cost_based | **Implemented** |
| Circuit breaker + retry/backoff | **Implemented** |
| Provider health + quota windows (persisted) | **Implemented** |
| Human override (`--model`, set-supervisor) | **Implemented** |
| Streaming foundation | **Implemented** |
| Live multi-provider smoke harness | **Implemented** (keys/Ollama required on host) |
| Contextual bandit / RL routing | **Planned** (Track H) |

## 3. Models & discovery

| Feature | Status |
|---------|--------|
| Model registry from `config/models.json` | **Implemented** |
| `list-models --refresh` (+ `SUPERAI_MODELS_URL`) | **Implemented** |
| Broad provider call paths (OpenAI-compat, Anthropic, Google, Ollama, …) | **Implemented** |
| External AI CLI discovery (Claude Code, Aider, …) | **In progress** (Track H) |

## 4. Self-learning & memory

| Feature | Status |
|---------|--------|
| Memory Palace (ChromaDB + offline fallback) | **Implemented** |
| Local embeddings (hash / sentence-transformers / EmbeddingGemma path) | **Implemented** |
| Named collections facade (learnings, skills, tasks, reflections) | **Implemented** |
| Learn from outcomes; conflicts; distill; decay | **Implemented** |
| Mid-task memory injection | **Implemented** |
| Human feedback CLI | **Implemented** |
| Knowledge evolution CLI (`evolve`) | **Implemented** |
| Wings & rooms + provenance | **Planned** (Track I) |

## 5. Skills

| Feature | Status |
|---------|--------|
| Markdown skills + index | **Implemented** |
| Inject relevant skills into prompts | **Implemented** |
| Auto-create from repeated success (sandbox) | **Implemented** |
| Promote / rollback / success_rate | **Implemented** |

## 6. Backup & security

| Feature | Status |
|---------|--------|
| AES-256-GCM + zstd encrypted backups | **Implemented** |
| Incremental + retention | **Implemented** |
| Verify + restore local | **Implemented** |
| Auto-backup on clean exit | **Implemented** |
| rclone cloud push/pull/restore | **Implemented** (rclone must be configured) |

## 7. CLI & UX

| Feature | Status |
|---------|--------|
| Typer CLI + Rich output | **Implemented** |
| Progress bars on multi-step runs | **Implemented** |
| Suggested fixes on common errors | **Implemented** |
| Shell completion | **Implemented** (`--install-completion`) |
| Terminal dashboard module | **Partial** (exists; deeper live wiring Track H) |
| Web dashboard | **Planned** (Track H) |

## 8. Advanced / ecosystem (required later tracks)

External CLI delegation, tool proposals + human approval, dual dashboards, RL routing, MCP-deep context, agentic debate patterns, n8n/cloud/Notion integrations, advanced first-run discovery — see **Tracks H–I** on `TASKBOARD.md`.
