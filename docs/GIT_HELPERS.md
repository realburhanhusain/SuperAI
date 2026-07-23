# Git Commit & Branch Naming Helpers (S116)

## Overview

SuperAI includes helper tools (`src/core/git_helpers.py`) to standardize git workflows according to Conventional Commits and clean branch naming specifications across multi-agent collaborations.

---

## Conventions

### Branch Names
Format: `<type>/<slug-description>`
Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci`

Example: `feat/prompt-injection-defense`

### Conventional Commit Messages
Format: `<type>(<scope>): <short summary>`

Example: `feat(safety): add prompt injection sanitization and context wrapping`

---

## API & CLI Usage

```python
from core.git_helpers import suggest_branch_name, suggest_commit_message

# Branch recommendation
branch = suggest_branch_name("add process exit code taxonomy", branch_type="feat")
# Output: "feat/add-process-exit-code-taxonomy"

# Commit recommendation
msg = suggest_commit_message("add exit codes module", scope="cli", commit_type="feat")
# Output: "feat(cli): add exit codes module"
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_git_helpers_s116.py`.
