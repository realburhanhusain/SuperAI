#!/usr/bin/env bash
# V6 N286 sample pre-commit hook — plan-mode dry check
set -euo pipefail
if command -v superai >/dev/null 2>&1; then
  superai doctor --quick 2>/dev/null || true
fi
