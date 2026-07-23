# SuperAI Process Exit Codes (M080)

## Overview

SuperAI implements standardized, trustworthy process exit codes (`src/core/exit_codes.py`) across all CLI entry points, background daemons (`superai daemon`), and child subprocesses.

This guarantees predictable exit semantics when integrating SuperAI into CI/CD pipelines, Kubernetes CronJobs, Windows Task Scheduler, and outer orchestrators.

---

## Exit Code Taxonomy

| Code | Constant | Meaning / Trigger Scenario |
|------|----------|----------------------------|
| `0` | `OK` | Successful execution without errors. |
| `1` | `GENERAL` | General unmapped execution failure. |
| `2` | `USAGE` | Invalid CLI arguments, schema validation error, or missing required parameter. |
| `3` | `BUDGET` | Spend budget ceiling exceeded (`M001`). |
| `4` | `PERMISSION` | Permission model block (`ask`/`plan` mode required or unconfirmed yolo). |
| `5` | `READINESS` | LLM provider readiness check failed or missing API credentials (`M010`). |
| `6` | `TIMEOUT` | Subprocess execution or HTTP network request timed out (`M018`). |
| `7` | `PROVIDER` | LLM provider remote API failure (5xx server error, rate limit). |
| `8` | `CANCELLED` | Operation cooperatively cancelled by user interrupt (`Ctrl+C`) or `CancelToken` (`M017`). |
| `9` | `JAIL` | Workspace jail sandbox violation (`M006`). |
| `99` | `INTERNAL` | Unexpected internal crash or unhandled runtime failure. |

---

## Usage in Code

```python
from core.exit_codes import from_result, from_exception, BUDGET, OK

# Mapping result dictionary payload
result = {"ok": False, "error_code": "budget", "message": "Daily ceiling hit"}
exit_code = from_result(result)  # returns 3

# Mapping exception
try:
    run_task()
except Exception as e:
    code = from_exception(e)
    sys.exit(code)
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_exit_codes_m080.py`.
CLI inspection available via:

```bash
superai exit-codes
```
