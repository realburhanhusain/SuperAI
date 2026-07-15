#!/usr/bin/env bash
# SuperAI bootstrap: install Python package + optional host tools / Postgres (not bundled).
# Usage:
#   ./scripts/bootstrap.sh
#   ./scripts/bootstrap.sh --profile agentic --live
#   ./scripts/bootstrap.sh --interactive
#   ./scripts/bootstrap.sh --with-postgres --live --yes
#   ./scripts/bootstrap.sh --extras dev,web --skip-host-tools
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PROFILE="core"
EXTRAS="dev"
LIVE=0
SKIP_HOST=0
SKIP_PIP=0
INTERACTIVE=0
WITH_POSTGRES=0
SKIP_POSTGRES=0
YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --extras) EXTRAS="$2"; shift 2 ;;
    --live) LIVE=1; shift ;;
    --skip-host-tools) SKIP_HOST=1; shift ;;
    --skip-pip) SKIP_PIP=1; shift ;;
    --interactive) INTERACTIVE=1; shift ;;
    --with-postgres) WITH_POSTGRES=1; shift ;;
    --skip-postgres) SKIP_POSTGRES=1; shift ;;
    --yes|-y) YES=1; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

echo "== SuperAI bootstrap =="
echo "Repo: $ROOT"

if [[ "$SKIP_PIP" -eq 0 ]]; then
  echo "pip install -e .[${EXTRAS}]"
  python -m pip install -e ".[${EXTRAS}]"
fi

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ "$INTERACTIVE" -eq 1 || "$WITH_POSTGRES" -eq 1 ]]; then
  echo "Running SuperAI install wizard..."
  ARGS=(install)
  if [[ "$INTERACTIVE" -eq 1 ]]; then ARGS+=(--interactive); else ARGS+=(--non-interactive); fi
  if [[ "$WITH_POSTGRES" -eq 1 ]]; then ARGS+=(--with-postgres); fi
  if [[ "$SKIP_POSTGRES" -eq 1 ]]; then ARGS+=(--skip-postgres); fi
  if [[ "$SKIP_HOST" -eq 1 ]]; then ARGS+=(--skip-host-tools); else
    ARGS+=(--host-tools-profile "$PROFILE" --install-host-tools)
  fi
  if [[ "$LIVE" -eq 1 || "$YES" -eq 1 ]]; then ARGS+=(--live); fi
  if [[ "$YES" -eq 1 ]]; then ARGS+=(--yes); fi
  python -m scli "${ARGS[@]}" || true
  echo "Done. Next: superai doctor"
  exit 0
fi

if [[ "$SKIP_HOST" -eq 1 ]]; then
  echo "Skipping host tools."
  exit 0
fi

echo "Host tools check (profile=${PROFILE})..."
python -m scli host-tools check --profile "$PROFILE" || true

if [[ "$LIVE" -eq 1 ]]; then
  echo "LIVE host tools install..."
  python -m scli host-tools install --profile "$PROFILE" --live
else
  echo "Dry-run host tools install..."
  python -m scli host-tools install --profile "$PROFILE" --dry-run
  echo ""
  echo "To actually install: ./scripts/bootstrap.sh --profile ${PROFILE} --live"
  echo "Interactive: ./scripts/bootstrap.sh --interactive"
  echo "Postgres opt-in: ./scripts/bootstrap.sh --with-postgres --live --yes"
  echo "  # or: superai install"
fi

echo "Done. Next: superai doctor  |  superai install"
