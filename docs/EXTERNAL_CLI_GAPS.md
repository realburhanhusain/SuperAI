# External CLI integration gaps — closed

**Updated:** 2026-07-15  
**Module:** `src/core/external_cli.py`

## Observations → status

| Observation | Status |
|-------------|--------|
| Module felt standalone | **Closed** — single integration path for inject/write-back/audit |
| Weak Memory Palace / context / output wrapping | **Closed** — `with_context` + `write_memory` defaults on `ExternalCLITool.run` |
| Unclear orchestrator supervisor–worker use | **Closed** — `cli_delegate_workers` + `run_as_worker` + ModelCaller `cli:*` |

## Integration graph

```text
Orchestrator (cli_delegate_workers)
    └─ model = cli:claude ──► ModelCaller._call_external_cli
                                    └─ ExternalCLITool.run
                                         ├─ central_memory.inject_context
                                         ├─ subprocess / dry-run
                                         ├─ central_memory.write_back
                                         ├─ LearningEngine.learn_from_step (if step_id)
                                         └─ AuditLog

cli_pool / cli-parallel ──► ExternalCLITool.run (same path)
cli-run ──► ExternalCLITool (CLI layer)
```

## Config

| Key | Default | Meaning |
|-----|---------|---------|
| `cli_delegate_workers` | `false` | Route worker/implementer steps to external CLIs |
| `cli_delegate_preferred` | `null` | Preferred CLI name when delegating |

```powershell
superai config set cli_delegate_workers true
superai config set cli_delegate_preferred aider
superai run "implement feature X" -v
# or force: superai run "…" --model cli:claude
```

## Envelope metadata

`CLIResultEnvelope.metadata` now includes: `context_id`, `memory_count`, `memory_write`, `role`, `workflow_id`, `task_id`, `step_id`, `audited`, `integrated`.
