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
src/superai/
  cli/main.py, dashboard.py
  web_app.py
  core/
    orchestrator.py, task_planner.py, task_result.py
    model_*.py, load_balancer.py, bandit_router.py
    memory_*.py, embeddings.py, learning_engine.py, skills.py
    backup_manager.py, preferences.py, time_travel.py
    external_cli.py, mcp_context.py, tool_proposals.py
    messengers.py, ecosystem.py, observability.py
    council.py, agentic.py, hierarchy.py
    databao_adapter.py, vega_charts.py, plugin_registry.py
    discovery.py, wings.py, config.py, history.py, errors.py
```

## Runtime data (`~/.superai/`)

| Path | Content |
|------|---------|
| `config.json` | User settings |
| `history/` | Task run JSON |
| `memory/` | Chroma / memory stores |
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
