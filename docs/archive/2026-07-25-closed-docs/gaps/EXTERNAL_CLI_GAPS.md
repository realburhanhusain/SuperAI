# External CLI integration gaps — closed

**Updated:** 2026-07-16  
**Module:** `src/core/external_cli.py` · `src/core/multi_cli_advisory.py`

## Observations → status

| Observation | Status |
|-------------|--------|
| Module felt standalone | **Closed** — single integration path for inject/write-back/audit |
| Weak Memory Palace / context / output wrapping | **Closed** — `with_context` + `write_memory` defaults on `ExternalCLITool.run` |
| Unclear orchestrator supervisor–worker use | **Closed** — `cli_delegate_workers` + `run_as_worker` + ModelCaller `cli:*` |
| Council/pr-review ignore CLIs by default | **Closed** — prefer available `cli:*` members; pr-review runs multi-CLI board |
| No auto multi-CLI review | **Closed** — `cli_delegate_reviewers` (default false; opt-in) + `superai review` / `advise` |
| No advisor role | **Closed** — `advisor` role + gemini default_role=advisor |
| Weak CLI args / PATH errors | **Closed** — alt templates, probe(), install_hint on miss |
| Freeform review only | **Closed** — structured protocol v1 (verdict/findings/confidence) |
| CLI-only boards (no API models) | **Closed** — unified `member_selection` + `superai members`; mix API+CLI |
| No CLI inner model pick | **Closed** — `cli:name@MODEL`, `--cli-model` / `-M`, `model_flag` on specs |
| ModelCaller/council dropped `@MODEL` | **Closed** — `split_cli_selector` + `cli_model` through ModelCaller/council/orchestrator |
| Council defaults CLI-only | **Closed** — `default_council_members(prefer=mixed)` + API keys when configured |
| No CLI inner-model discovery | **Closed** — `cli_models.py` curated+registry+optional live probe; `members --pick` |

## Unified members (API + CLI)

When provider API keys are configured (or mock mode), those registry models are
selectable **alongside** PATH CLIs for review / advise / council.

```text
superai members --available              # API + PATH CLIs + inner models
superai members --available --live-probe # also try CLI help/list (cached)
superai members --pick                   # interactive multi-select
superai run "implement X" --pick-workers
superai review "auth design" --pick
superai review "auth design" -m gpt-4o,cli:gemini@gemini-2.5-pro,cli:grok
superai advise "ship tonight?" --prefer mixed
superai council "pick architecture" --pick
superai cli-run gemini@gemini-2.5-flash "summarize this PR" --dry-run
```

| Selector | Meaning |
|----------|---------|
| `gpt-4o` | API model from registry (needs key / mock) |
| `cli:gemini` | External CLI, default model |
| `cli:gemini@MODEL` / `gemini@MODEL` | CLI + inner model (`model_flag`) |
| `--prefer mixed\|cli\|api` | Auto-pick when `--members` / `--models` omitted |

Module: `src/core/member_selection.py` · protocol `superai.multi_member_review.v2`

## Natural language (`superai ask`) — universal agent front door

Like Claude Code / Gemini / Codex: **say what you want**. Specialized SuperAI
features are auto-routed; anything else becomes an orchestrated agent task.

```text
superai ask                         # interactive REPL
superai ask "list available models and clis"
superai ask "review the auth design with gpt-4o and gemini dry-run"
superai ask "advise should we ship tonight prefer cli"
superai ask "council on architecture let me pick"
superai ask "implement rate limiting with gpt-4o and claude"
superai ask "run doctor" / "search memory for postgres" / "plan a FastAPI app"
superai ask "what should I refactor next?"   # universal agent → run
superai ask "review X" --plan-only
```

Routes include: members, review, advise, council, doctor, discover, plan, tdd,
pr-review, memory, palace, backup, budget, host-tools, debate, github, web search,
cli-run, and **run** (default agent). Module: `src/core/nl_intent.py`.

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
| `worker_prefer` | `mixed` | Worker pool auto-pick: mixed \| api \| cli \| router |
| `worker_members` | `null` | Explicit pool e.g. `gpt-4o,cli:gemini@MODEL` |
| `worker_max` | `5` | Max size of primary + failover pool |
| `cli_delegate_workers` | `false` | Legacy: force `worker_prefer=cli` |
| `cli_delegate_preferred` | `null` | Preferred CLI prepended to worker pool |
| `cli_delegate_reviewers` | `false` | Opt-in multi-member board on orchestrator critic path |

```powershell
superai members --available
superai run "implement feature X" --workers gpt-4o,cli:gemini@flash,cli:claude -v
superai run "…" --worker-prefer cli
superai config set worker_prefer mixed
superai config set worker_members "gpt-4o,cli:codex"
superai config set cli_delegate_workers true   # legacy CLI-first
superai config set cli_delegate_reviewers true # critic board
# force one worker: superai run "…" -m cli:claude@… / -m gpt-4o
```

## Envelope metadata

`CLIResultEnvelope.metadata` now includes: `context_id`, `memory_count`, `memory_write`, `role`, `workflow_id`, `task_id`, `step_id`, `audited`, `integrated`.
