# Dependency Upgrade Assistant (S112)

## Overview

SuperAI provides an automated dependency upgrade assistant (`src/core/dep_upgrade.py`) to audit requirements and package manifests for upgradable packages and breaking change risks.

---

## Features

1. **Manifest Audit (`check_upgradable_dependencies`)**
   * Parses `pyproject.toml`, `requirements.txt`, and `package.json` files to extract version constraints and recommend safe upgrade strategies.

---

## API & CLI Usage

```python
from core.dep_upgrade import check_upgradable_dependencies

res = check_upgradable_dependencies("requirements.txt")
print(f"Total: {res.total_dependencies}, Recommendations: {len(res.recommendations)}")
```

### CLI Command

```bash
superai check upgrades pyproject.toml
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_dep_upgrade_s112.py`.

## Depth closeout (2026-07-24)

Risk-ranked pins + write_upgrade_plan(--apply writes review files only).
