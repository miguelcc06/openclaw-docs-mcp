#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# shellcheck source=/dev/null
source "$PROJECT_DIR/config.env"

if [[ "${SYNC_ENABLED:-true}" != "true" ]]; then
  echo "SYNC_ENABLED is not true; skipping sync."
  exit 0
fi

exec "$PROJECT_DIR/.venv/bin/openclaw-docs-mcp" sync
