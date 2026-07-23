# Per-Command Budget Overrides (S132)

## Overview

SuperAI provides fine-grained, per-command spend budget overrides (`src/core/command_budget.py`) allowing developers to set granular cost ceilings for individual CLI tools, subagents, or execution routes.

---

## Features

1. **Per-Command Limits (`set_command_budget`, `get_command_budget`)**
   * Configures spending limits in USD for specific commands (e.g. `run`, `council`, `bakeoff`).

2. **Budget Guard Verification (`check_command_budget_guard`)**
   * Evaluates current command spend against configured command-level budget limits prior to execution.

---

## API & CLI Usage

```python
from core.command_budget import set_command_budget, check_command_budget_guard

# Set $0.50 budget limit for 'council' command
set_command_budget("council", 0.50)

# Check spend guard
guard = check_command_budget_guard("council", current_spend_usd=0.60)
if not guard.allowed:
    print("Command budget exceeded:", guard.message)
```

### CLI Command

```bash
superai budget command set council 0.50
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_command_budget_s132.py`.
