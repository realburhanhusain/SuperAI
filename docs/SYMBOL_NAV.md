# Symbol-Aware Code Navigation (S108)

## Overview

SuperAI provides AST-based symbol indexing and code navigation (`src/core/symbol_nav.py`) to discover functions, classes, methods, and constants across python codebases without relying on fuzzy text grep.

---

## Features

1. **AST Symbol Extraction (`index_symbols_in_file`)**
   * Extracts strongly-typed symbol metadata (kind, line number, class name, docstring) via AST parsing.

2. **Repository Symbol Search (`search_symbols`)**
   * Queries indexed symbols by function name, class name, or method signature.

---

## API & CLI Usage

```python
from core.symbol_nav import index_symbols_in_file, search_symbols

# Index file symbols
symbols = index_symbols_in_file("src/core/git_helpers.py")
for s in symbols:
    print(f"[{s.kind}] {s.name} at line {s.line_number}")

# Search symbols across codebase
results = search_symbols("suggest_branch")
```

### CLI Command

```bash
superai symbol search suggest_branch
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_symbol_nav_s108.py`.
