# PR Explanation Generator with File-Level Findings (S110)

## Overview

SuperAI provides automated Pull Request summary generation (`src/core/pr_explainer.py`) to parse git diff patches, compute file addition/deletion statistics, and generate structured Markdown PR descriptions with per-file findings.

---

## Features

1. **Git Patch Parsing (`parse_git_diff`)**
   * Computes file-level additions, deletions, and line counts from raw git diffs or commit ranges.

2. **Markdown PR Summary Generation (`generate_pr_explanation`)**
   * Generates formatted Markdown PR descriptions featuring overall change summaries and per-file findings tables.

---

## API & CLI Usage

```python
from core.pr_explainer import generate_pr_explanation, generate_pr_explanation_from_repo

# Generate PR summary from diff string
explanation = generate_pr_explanation(raw_git_diff_text)
print(explanation.markdown_output)

# Generate PR summary directly from active git repo
repo_expl = generate_pr_explanation_from_repo()
```

### CLI Command

```bash
superai git explain-pr
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_pr_explainer_s110.py`.
