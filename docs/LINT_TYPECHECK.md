# Post-Edit Lint & Typecheck Integration (S106)

## Overview

SuperAI provides automated post-edit linting and syntax/AST verification (`src/core/lint_typecheck.py`) to validate Python files post-edit, preventing syntax errors and catching bad code patterns before committing.

---

## Features

1. **AST & Syntax Verification (`check_python_syntax_and_ast`)**
   * Parses Python files into AST to detect syntax errors (`E999`), unreadable files (`E902`), and bare `except:` statements (`E722`).

2. **Batch Post-Edit Verification (`run_post_edit_checks`)**
   * Validates multiple modified files simultaneously, returning structured issue reports.

---

## API & CLI Usage

```python
from core.lint_typecheck import check_python_syntax_and_ast, run_post_edit_checks

# Check a single python file
res = check_python_syntax_and_ast("src/core/git_helpers.py")
if not res.is_clean:
    print("Lint issues found:", res.issues)

# Batch check multiple files
report = run_post_edit_checks(["src/core/exit_codes.py", "src/core/git_helpers.py"])
```

### CLI Command

```bash
superai check lint src/core/git_helpers.py
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_lint_typecheck_s106.py`.
