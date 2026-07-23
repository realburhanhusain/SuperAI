# License & Compliance Check on Dependencies (S115)

## Overview

SuperAI provides automated open-source license scanning (`src/core/license_check.py`) to audit dependency manifests (`pyproject.toml`, `package.json`, `requirements.txt`) for restrictive or copyleft (GPL/AGPL) licenses prior to production deployment.

---

## Features

1. **Manifest Scanning (`scan_dependency_licenses`)**
   * Parses Python (`pyproject.toml`, `requirements.txt`) and Node.js (`package.json`) manifest files.

2. **Compliance Warnings**
   * Flags copyleft GPL/AGPL packages that pose IP risk for proprietary redistribution.

---

## API & CLI Usage

```python
from core.license_check import scan_dependency_licenses

res = scan_dependency_licenses("package.json")
if not res.is_compliant:
    print("License compliance warnings found:", res.issues)
```

### CLI Command

```bash
superai check license pyproject.toml
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_license_check_s115.py`.

## Depth closeout (2026-07-24)

Offline curated SPDX map + weak-copyleft category; not a live license API.
