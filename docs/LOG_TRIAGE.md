# Log Triage & Stack Trace Analyzer (S124)

## Overview

SuperAI provides log triage and stack trace analysis capabilities (`src/core/log_triage.py`) to parse error logs, extract root cause stack frames, and generate targeted recommendations.

---

## Features

1. **Stack Trace Parsing (`triage_stack_trace`)**
   * Extracts exception class (`KeyError`, `AttributeError`, `TypeError`), error details, and stack frame locations (`filename`, `line_number`, `function_name`).

2. **Automated Diagnostic Recommendations (`_generate_suggested_fix`)**
   * Maps root cause exception taxonomy to specific code fix suggestions.

---

## API & CLI Usage

```python
from core.log_triage import triage_stack_trace, triage_log_file

log_text = '''
Traceback (most recent call last):
  File "src/core/model_caller.py", line 45, in call
    result = payload["data"]
KeyError: 'data'
'''

triage = triage_stack_trace(log_text)
print("Exception:", triage.exception_type)
print("Top Frame:", triage.top_frame.filename, triage.top_frame.line_number)
print("Fix Suggestion:", triage.suggested_fix)
```

### CLI Command

```bash
superai triage-log app.log
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_log_triage_s124.py`.
