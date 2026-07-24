# CLI Middleware Inventory

Maps public commands to budget/mutation middleware classes (M001 / V5-M1).

**Updated:** 2026-07-24 (AGY residual closeout — product wiring + tests)

## SPEND (require `budget_precheck` / ModelCaller pre_call)

| Command / path | `command_name` | Module entry |
|----------------|----------------|--------------|
| council | `council` | `Council.run` |
| bakeoff | `bakeoff` | `model_bakeoff.bakeoff` |
| compare | `compare` | `model_compare.compare_models` |
| pr_review | `pr_review` | `pr_review.review_diff` |
| multi_cli / advise boards | `multi_cli` | `multi_cli_advisory.multi_cli_board` |
| goals execute | `goals` | `GoalStore.execute_due` |
| board-preflight | `board-preflight` | `board_preflight.estimate_board` |
| live-smoke | `live-smoke` | `live_smoke_complete.run_phase6_smoke` |
| web `/api/superai/run` | `web` | `web_app.api_superai_run` |
| stream | `stream` | `ModelCaller.call_stream` |
| MCP spend tools | `mcp:{name}` | `mcp_safety.wrap_mcp_tool` |
| ask / do / agent | via ModelCaller | `call` → `pre_call` |

## MUTATING (local state; permission-aware)

- config set, backup/restore, memory store paths, dataset/ingest, session promote

## FREE (read-only / no external budget)

- status, doctor, plan, history, version, learning list/status, smoke-preflight, host-tools list

## Tests

```text
pytest tests/test_cli_middleware.py tests/test_spend_path_assertions.py -q
```
