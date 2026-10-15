#!/bin/bash
set -euo pipefail

# Finder's double-clickable entry point for AuraFlow.
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/bash "${SCRIPT_DIR}/scripts/start.sh"
