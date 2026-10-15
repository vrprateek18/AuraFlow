#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
APP_EXECUTABLE="${PROJECT_DIR}/build/AuraMotion.app/Contents/MacOS/AuraMotion"
SOURCE_SENTINEL="${PROJECT_DIR}/Sources/AuraMotionCore/App/AppEnvironment.swift"

if [ ! -x "${APP_EXECUTABLE}" ]; then
    echo "==> AuraMotion build not found at ${APP_EXECUTABLE}"
    echo "    Run ./scripts/build_app.sh first."
    exit 1
fi

if [ "${1:-}" = "--check" ]; then
    echo "==> AuraMotion build found at ${APP_EXECUTABLE}"
    if [ -f "${SOURCE_SENTINEL}" ] && [ "${SOURCE_SENTINEL}" -nt "${APP_EXECUTABLE}" ]; then
        echo "==> Warning: the app bundle is older than the source. Run ./scripts/build_app.sh."
    fi
    exit 0
fi

if [ -f "${SOURCE_SENTINEL}" ] && [ "${SOURCE_SENTINEL}" -nt "${APP_EXECUTABLE}" ]; then
    echo "==> Warning: the app bundle is older than the source. Run ./scripts/build_app.sh first."
fi

echo "==> Stopping any running AuraMotion instance..."
pkill -x AuraMotion 2>/dev/null || true
sleep 0.5

echo "==> Launching AuraMotion Pro..."
nohup "${APP_EXECUTABLE}" > /dev/null 2>&1 &
PID=$!
sleep 1.5

if ps -p "$PID" > /dev/null; then
    echo "==> AuraMotion Pro running successfully (PID: $PID)"
    if [ -f "/tmp/auramotion_perms.log" ]; then
        cat /tmp/auramotion_perms.log
    fi
else
    echo "==> Failed to start AuraMotion Pro"
    exit 1
fi
