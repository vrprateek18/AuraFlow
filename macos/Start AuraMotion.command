#!/bin/bash
set -euo pipefail

# Finder's double-clickable entry point.  Keep this in the project folder and
# use it instead of opening the .app bundle directly so AuraMotion starts via
# the same Terminal-backed path as ./scripts/start.sh.
SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
exec /bin/bash "${SCRIPT_DIR}/scripts/start.sh"
