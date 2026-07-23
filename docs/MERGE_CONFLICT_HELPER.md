# Safe Conflict Assistance for Merges (S117)

## Overview

SuperAI provides automated git merge conflict parsing and resolution assistance (`src/core/merge_conflict_helper.py`) to parse conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) and inspect conflicting code blocks.

---

## Features

1. **Conflict Marker Parsing (`parse_conflict_markers`)**
   * Extracts local (`OURS`) vs remote (`THEIRS`) conflicting code blocks and line numbers.

---

## API & CLI Usage

```python
from core.merge_conflict_helper import analyze_file_conflicts, parse_conflict_markers

result = analyze_file_conflicts("src/core/git_helpers.py")
if result.has_conflicts:
    print(f"Conflicts found ({result.conflict_count}):", result.recommendation)
```

### CLI Command

```bash
superai git resolve-conflicts src/core/git_helpers.py
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_merge_conflict_helper_s117.py`.
