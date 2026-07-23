# Prompt-Injection Security Defenses for Tool Loops (M015)

## Overview

Indirect Prompt Injection occurs when untrusted content (web pages, files, database records, external API responses) contains adversarial instructions designed to hijack the LLM's control flow or break out of workspace boundaries.

SuperAI provides a defense-in-depth module (`src/core/prompt_injection.py`) to scan, sanitize, and isolate untrusted content before it reaches LLM tool loops.

---

## Defense Mechanisms

1. **Threat Pattern Scanning (`scan_for_injection_threats`)**
   * Scans text for instruction hijacking (`ignore all previous instructions`), role overrides (`you are now a new AI`), delimiter spoofing (`<system>`, `[INST]`), and hidden zero-width unicode characters.

2. **Text Sanitization (`sanitize_tool_input`)**
   * Strips zero-width unicode characters (`\u200b`, `\u200c`, `\ufeff`).
   * Escapes dangerous system delimiter tags to prevent prompt injection boundary spoofing.

3. **Untrusted Context Isolation (`wrap_untrusted_context`)**
   * Encloses retrieved tool outputs inside XML boundary tags with explicit system instructions prohibiting instruction execution.

---

## API Usage

```python
from core.prompt_injection import scan_for_injection_threats, wrap_untrusted_context

# 1. Scan untrusted content from tool/web
result = scan_for_injection_threats(untrusted_html)
if not result.is_safe:
    logger.warning("Prompt injection attempt detected: %s", result.threats)

# 2. Wrap content safely for LLM context
safe_prompt_payload = wrap_untrusted_context(untrusted_html, source_label="web_fetch")
```

---

## Verification & Testing

Unit test coverage is enforced in `tests/test_prompt_injection_m015.py`.
