#!/bin/sh
set -eu

if [ "${AEGIS_SCAN_ENGINE:-nmap}" = "nmap" ]; then
    NMAP_BINARY="${AEGIS_NMAP_PATH:-nmap}"
    if [ -z "$NMAP_BINARY" ]; then
        NMAP_BINARY="nmap"
    fi
    "$NMAP_BINARY" --version >/dev/null
fi

exec uvicorn app.main:app --host "${AEGIS_HOST:-0.0.0.0}" --port "${AEGIS_PORT:-8000}"
