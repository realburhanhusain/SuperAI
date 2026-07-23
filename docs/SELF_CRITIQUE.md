# Self-Critique Pass Before Claiming Done (S104)

## Overview

SuperAI provides automated self-critique audits (`src/core/self_critique.py`) to evaluate code quality, docstrings, and error handling prior to declaring tasks complete.

---

## Features

1. **AST Quality Audit (`run_self_critique_pass`)**
   * Inspects AST nodes for module/function docstrings, bare `except:` blocks, and type safety constraints.

2. **Quality Score Calculation**
   * Computes a 0–100 quality score and returns structured findings.

---

## API & CLI Usage

```python
from core.self_critique import run_self_critique_pass

critique = run_self_critique_pass("src/core/git_helpers.py")
print(f"Score: {critique.score}/100, Passed: {critique.passed}")
```

### CLI Command

```bash
superai check critique src/core/git_helpers.py
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_self_critique_s104.py`.

## Depth closeout (2026-07-24)

S104 now checks: module/public docs, return annotations, bare/silent except, mutable defaults, TODO density.
