# Public Handler Contract Inventory (V4-M2)

This inventory explicitly maps all `TOP_30` CLI commands and handlers to their expected return dict schema. This document satisfies the V4-M2 requirements for contract stability and deterministic response shapes.

## Core Schema
Every handler must return a dict wrapped by `emit_public()` containing:
- `ok` (bool): `True` if successful, `False` otherwise.
- `status` (str): Status string (e.g., `"success"`, `"error"`, `"waiting_human"`).
- `contract` (str): Contract version identifier (e.g., `"superai.result.v1"`).
- `mock` (bool) or `live` (bool): Honesty metadata.
- `honesty` (str): `"MOCK"` or `"LIVE"`.
- `exit_code` (int): Internal exit code based on taxonomy.
- `error_code` (str): Standardized error identifier (if `ok` is `False`).

## TOP 30 Commands Mapping

### Execution / Agents
- `run`, `do`, `ask`, `agent`: 
  - Schema: Core + `model_used`, `duration`, `estimated_cost_usd`, `result` (dict or str).

### Ensembles
- `council`, `compare`, `bakeoff`:
  - Schema: Core + `participants` (list), `responses` (dict), `winner` (str), `estimated_cost_usd`.

### Reviews
- `review`, `advise`, `pr_review`:
  - Schema: Core + `findings` (list of dicts), `severity` (str), `suggestions` (list).

### Status / Observability
- `status`, `doctor`, `v6-status`:
  - Schema: Core + `version`, `config_path`, `checks` (list of dicts, for doctor).

### Learning / Memory
- `learning`, `learnings`, `reflect`, `history-search`, `conflicts`:
  - Schema: Core + `items` (list), `count` (int), `memory_stats` (dict).

### Testing / Diagnostics
- `smoke-harness`, `smoke-preflight`, `phase6-smoke`, `contract-smoke`:
  - Schema: Core + `passed` (int), `failed` (int), `details` (list).

### Workspaces
- `worktree-run`, `tenant-export`, `board-preflight`, `project-budget`:
  - Schema: Core + `workspace_id` (str), `path` (str), `budget_usd` (float).

### General Utilities
- `goals`, `explain-run`, `progress`, `profile-suggest`, `eval-golden`, `spend-report`, `models-refresh-openrouter`, `plugin-catalog`, `host-tools`, `ci-why`, `gates`:
  - Schema: Core + Specific context payload keys as defined in handlers.

*This file implements the V4-M2 requirement explicitly.*
