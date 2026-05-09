#!/bin/sh
set -eu

if [ "${AEGIS_SCAN_ENGINE:-nmap}" = "nmap" ]; then
    NMAP_BINARY="${AEGIS_NMAP_PATH:-nmap}"
    if [ -z "$NMAP_BINARY" ]; then
        NMAP_BINARY="nmap"
    fi
    # Validate the binary is a real nmap (--version outputs version info)
    "$NMAP_BINARY" --version 2>&1 | grep -qi "nmap" || {
        echo "ERROR: nmap binary at $NMAP_BINARY does not appear to be a valid nmap installation" >&2
        exit 1
    }
fi

exec uvicorn app.main:app \
    --host "${AEGIS_HOST:-0.0.0.0}" \
    --port "${AEGIS_PORT:-8000}" \
    --timeout-graceful-shutdown 25
