# SuperAI Architecture (as implemented)

```mermaid
flowchart TB
    subgraph User["User interfaces"]
        CLI[superai CLI Typer+Rich]
        Dash[Terminal dashboard]
        Web[FastAPI web memory/charts/dashboard]
    end

    subgraph Core["Core"]
        Orch[SuperAIOrchestrator]
        Plan[TaskPlanner parallel-aware]
        Hist[TaskHistory]
        TR[TaskResult Pydantic]
        Cfg[Config + Logger]
    end

    subgraph Routing["Routing & resilience"]
        Router[ModelRouter scoring + bandit]
        LB[LoadBalancer + CircuitBreaker]
        Health[ProviderHealthStore]
        Reg[ModelRegistry]
        Caller[ModelCaller + stream]
    end

    subgraph Intel["Intelligence"]
        Learn[LearningEngine]
        Mem[MemoryPalace + embeddings]
        Skills[SkillsManager]
        Pref[UserPreferenceModel]
        Council[Council + Agentic]
        Hier[HierarchicalDelegator]
    end

    subgraph Ext["External & ecosystem"]
        ExtCLI[ExternalCLITool]
        MCP[MCPContextPack]
        Msg[MessengerBus]
        Eco[EcosystemHub]
        Data[DatabaoAdapter + Vega]
        Plug[PluginRegistry]
    end

    subgraph Backup["Backup"]
        BM[BackupManager AES-GCM + zstd]
        Rclone[rclone push/pull]
    end

    CLI --> Orch
    Dash --> Orch
    Web --> Mem
    Web --> Dash
    Orch --> Plan
    Orch --> Hist
    Orch --> TR
    Orch --> Router
    Orch --> Caller
    Orch --> Learn
    Orch --> Skills
    Orch --> Pref
    Router --> Reg
    Router --> Health
    Caller --> LB
    Learn --> Mem
    ExtCLI --> MCP
    Orch --> BM
    BM --> Rclone
    CLI --> Msg
    CLI --> Eco
    CLI --> Data
    CLI --> Council
    CLI --> Hier
```

## Package layout

```
src/
  cli/                 # directory name (import package: scli)
    main.py            # Typer app — entry: superai = "scli.main:app"
    dashboard.py
    web_app.py
  core/                # import package: core
    orchestrator.py, task_planner.py, task_result.py
    model_*.py, load_balancer.py, bandit_router.py
    memory_*.py, embeddings.py, learning_engine.py, skills.py
    …
```

Imports: `from core.…` and `from scli.…`  
(Note: the CLI package is imported as `scli` because a third-party `cli.py` on some systems shadows the name `cli`.)

## Wave-2 surfaces (2026-07-14)

- Safety: `approval_tui`, `keyring_store`, `workspace`, `compliance`, `secrets`  
- Product: `chat_session`, `tdd_loop`, `diff_edit`, `workspace_index`, `doctor`  
- Interop: `mcp_server`, `langgraph_export`, PWA `/pwa/`, VS Code `extensions/vscode-superai`  
- Memory: FAISS backend (`SUPERAI_MEMORY_BACKEND=faiss`), GDPR forget/TTL, encrypted sync  

## Runtime data (`~/.superai/`)

| Path | Content |
|------|---------|
| `config.json` | User settings |
| `history/` | Task run JSON |
| `memory/` | Memory Palace store (SQLite cosine default file; Postgres+pgvector when DSN set) |
| `skills/` | Markdown skills + index |
| `backups/` | Encrypted archives |
| `.backup_key` | AES key (protect) |
| `provider_health.json` | Health + quotas |
| `bandit_state.json` | Bandit arms |
| `contexts/` | MCP context packs |
| `plugins/` | Local plugin manifests |
| `charts/` | Generated Vega HTML |
| `feedback.jsonl` | Cross-surface feedback |
| `messenger_log.jsonl` | Messenger bus log |

## Execution path

1. CLI `run` → `SuperAIOrchestrator.run_task`
2. Classify → plan steps (parallel edges allowed)
3. Topological batches: serial or ThreadPool for `can_run_parallel`
4. Per step: router (+bandit) → caller → LB/health
5. Aggregate → history + learn + preferences + bandit reward
6. Optional atexit incremental backup

## References

- Board: `TASKBOARD.md`
- Progress: `docs/PROGRESS.md`
- Plans: `implementation_plan_detailed.md`
