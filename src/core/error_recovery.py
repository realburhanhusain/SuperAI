"""
Error classification + recovery suggestions (S11).
"""

from __future__ import annotations

from typing import Any, Dict


def classify_error(exc: BaseException | str) -> Dict[str, Any]:
    msg = str(exc).lower()
    if any(x in msg for x in ("api key", "401", "unauthorized", "authentication", "forbidden", "403")):
        return {
            "class": "auth",
            "retryable": False,
            "suggestion": "Set the provider API key and `superai config set mock_mode false`, or stay in mock mode.",
        }
    if any(x in msg for x in ("rate limit", "429", "quota", "too many requests")):
        return {
            "class": "rate_limit",
            "retryable": True,
            "suggestion": "Wait and retry; switch provider; check superai provider-health.",
        }
    if any(x in msg for x in ("timeout", "timed out", "connection", "network", "dns", "unreachable")):
        return {
            "class": "network",
            "retryable": True,
            "suggestion": "Check network/VPN; retry; or use mock_mode true offline.",
        }
    if any(x in msg for x in ("budget", "exceeded")):
        return {
            "class": "budget",
            "retryable": False,
            "suggestion": "Raise limits with `superai budget set` or wait for daily reset.",
        }
    if any(x in msg for x in ("approval", "veto", "workspace", "escapes")):
        return {
            "class": "policy",
            "retryable": False,
            "suggestion": "Approve with cli-run --approve, answer HITL, or fix SUPERAI_WORKSPACE paths.",
        }
    if any(x in msg for x in ("model", "not found", "unknown model")):
        return {
            "class": "model",
            "retryable": True,
            "suggestion": "superai list-models; superai pin-model; or --model override.",
        }
    return {
        "class": "unknown",
        "retryable": False,
        "suggestion": "Run superai doctor; retry with --debug.",
    }
