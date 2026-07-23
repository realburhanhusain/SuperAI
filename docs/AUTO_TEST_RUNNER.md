# Auto Test Discovery & Impacted Test Runner (S105)

## Overview

SuperAI provides automated test discovery (`src/core/auto_test_runner.py`) to map modified source files directly to impacted test suites in `tests/`.

---

## Features

1. **Impacted Test Discovery (`find_impacted_tests`)**
   * Scans changed code files (e.g. `src/core/git_helpers.py`) and discovers associated test files (`tests/test_git_helpers_s116.py`).

2. **Automated Test Execution (`run_impacted_tests`)**
   * Runs targeted pytest execution on only the impacted test files, drastically reducing feedback loop latency.

---

## API & CLI Usage

```python
from core.auto_test_runner import find_impacted_tests, run_impacted_tests

# Discover tests for modified source files
tests = find_impacted_tests(["src/core/prompt_injection.py"])
# Output: ["tests/test_prompt_injection_m015.py"]

# Run impacted tests programmatically
result = run_impacted_tests(["src/core/prompt_injection.py"])
```

### CLI Command

```bash
superai test impacted src/core/prompt_injection.py
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_auto_test_runner_s105.py`.

## Depth closeout (2026-07-24)

Alias map + exact/prefix matcher (exact_prefix_alias).
