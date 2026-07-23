# Fix CI Failure from Log Paste (S109)

## Overview

SuperAI provides automated CI log parsing and failure diagnosis (`src/core/ci_fixer.py`) to extract test failures, missing dependencies, and syntax errors directly from CI build logs or pasted output.

---

## Features

1. **CI Log Parsing (`analyze_ci_log_paste`)**
   * Detects failing test files (`FAILED tests/test_foo.py::test_bar`), missing imports (`ModuleNotFoundError`), and build timeouts.

2. **Automated Fix Recommendations**
   * Generates specific patch instructions for each detected CI failure.

---

## API & CLI Usage

```python
from core.ci_fixer import analyze_ci_log_paste

ci_log = """
FAILED tests/test_git_helpers.py::test_suggest_commit - AssertionError
ModuleNotFoundError: No module named 'rich'
"""

result = analyze_ci_log_paste(ci_log)
print(result.summary_report)
```

### CLI Command

```bash
superai ci-fix ci_build.log
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_ci_fixer_s109.py`.

## Depth closeout (2026-07-24)

Repair plan JSON with patch snippets + steps; --plan-out on CLI.
