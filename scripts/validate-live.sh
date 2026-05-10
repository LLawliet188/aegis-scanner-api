#!/usr/bin/env bash
# validate-live.sh — post-deploy smoke test for the live Aegis Scanner stack.
#
# Usage:
#   ./scripts/validate-live.sh
#   BACKEND_URL=https://... FRONTEND_URL=https://... ./scripts/validate-live.sh
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-https://aegis-scanner-api.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://aegis-scanner-api.vercel.app}"

PASS=0
FAIL=0

_pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
_fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }

_check_status() {
    local label="$1" url="$2" expected="${3:-200}"
    local actual
    actual=$(curl -so /dev/null -w "%{http_code}" --max-time 20 "$url" 2>/dev/null || echo "000")
    if [ "$actual" = "$expected" ]; then
        _pass "$label → HTTP $actual"
    else
        _fail "$label → expected HTTP $expected, got $actual (URL: $url)"
    fi
}

_check_body() {
    local label="$1" url="$2" pattern="$3"
    local body
    body=$(curl -sf --max-time 20 "$url" 2>/dev/null || echo "")
    if echo "$body" | grep -q "$pattern"; then
        _pass "$label"
    else
        _fail "$label (pattern '$pattern' not found in response)"
    fi
}

_check_header() {
    local label="$1" url="$2" header_pattern="$3"
    local headers
    headers=$(curl -sI --max-time 20 "$url" 2>/dev/null || echo "")
    if echo "$headers" | grep -qi "$header_pattern"; then
        _pass "$label"
    else
        _fail "$label (pattern '$header_pattern' not found in headers)"
    fi
}

_check_cors_allowed() {
    local label="$1" url="$2" origin="$3"
    local headers
    headers=$(curl -si --max-time 20 -X OPTIONS "$url" \
        -H "Origin: $origin" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: content-type" 2>/dev/null || echo "")
    local status
    status=$(echo "$headers" | head -1 | awk '{print $2}')
    local acao
    acao=$(echo "$headers" | grep -i "access-control-allow-origin" | tr -d '\r' || true)
    if [ "$status" = "200" ] && echo "$acao" | grep -q "$origin" 2>/dev/null; then
        _pass "$label → $acao"
    else
        _fail "$label → HTTP $status, ACAO: $acao"
    fi
}

_check_cors_blocked() {
    local label="$1" url="$2" origin="$3"
    local status
    status=$(curl -so /dev/null -w "%{http_code}" --max-time 20 -X OPTIONS "$url" \
        -H "Origin: $origin" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: content-type" 2>/dev/null || echo "000")
    if [ "$status" != "200" ]; then
        _pass "$label → blocked (HTTP $status)"
    else
        _fail "$label → origin was NOT blocked (HTTP $status)"
    fi
}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Aegis Scanner — Live Deployment Validation"
echo " Backend:  $BACKEND_URL"
echo " Frontend: $FRONTEND_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "── Frontend ─────────────────────────────────────"
_check_status "Frontend loads"            "$FRONTEND_URL"          200
_check_body   "Frontend contains Vite app" "$FRONTEND_URL"          "<!doctype html"

echo ""
echo "── Backend health ───────────────────────────────"
_check_status "GET /v1/health"             "$BACKEND_URL/v1/health"          200
_check_body   "health.status = ok"         "$BACKEND_URL/v1/health"          '"status":"ok"'
_check_status "GET /v1/health/detailed"    "$BACKEND_URL/v1/health/detailed" 200
_check_body   "detailed health has memory" "$BACKEND_URL/v1/health/detailed" '"memory"'
_check_body   "detailed health has uptime" "$BACKEND_URL/v1/health/detailed" '"uptime_seconds"'

echo ""
echo "── Observability ────────────────────────────────"
_check_status "GET /v1/metrics (JSON)"     "$BACKEND_URL/v1/metrics" 200
_check_body   "metrics has uptime_seconds" "$BACKEND_URL/v1/metrics" '"uptime_seconds"'
# Prometheus text format requires Accept header; test via body content
PROM_BODY=$(curl -sf --max-time 20 -H "Accept: text/plain" "$BACKEND_URL/v1/metrics" 2>/dev/null || echo "")
if echo "$PROM_BODY" | grep -q "aegis_uptime_seconds"; then
    _pass "GET /v1/metrics (Prometheus text)"
else
    _fail "GET /v1/metrics (Prometheus text) — missing aegis_uptime_seconds"
    FAIL=$((FAIL + 1))
fi

echo ""
echo "── Request ID correlation ───────────────────────"
_check_header "X-Request-ID present in response" "$BACKEND_URL/v1/health" "x-request-id"
ECHOED=$(curl -sI --max-time 20 -H "X-Request-ID: test-live-validate" "$BACKEND_URL/v1/health" 2>/dev/null \
    | grep -i "x-request-id" | tr -d '\r')
if echo "$ECHOED" | grep -q "test-live-validate"; then
    _pass "X-Request-ID echoed back unchanged → $ECHOED"
else
    _fail "X-Request-ID not echoed (got: $ECHOED)"
fi

echo ""
echo "── CORS ─────────────────────────────────────────"
_check_cors_allowed "CORS preflight from Vercel origin" \
    "$BACKEND_URL/v1/scan" "$FRONTEND_URL"
_check_cors_blocked "CORS preflight from evil origin blocked" \
    "$BACKEND_URL/v1/scan" "https://evil.example.com"

echo ""
echo "── Scan API ─────────────────────────────────────"
SCAN_RESPONSE=$(curl -sf --max-time 20 -X POST "$BACKEND_URL/v1/scan" \
    -H "Content-Type: application/json" \
    -H "Origin: $FRONTEND_URL" \
    -d '{"target":"127.0.0.1","options":{"top_ports":10}}' 2>/dev/null || echo "")
if echo "$SCAN_RESPONSE" | grep -q '"scan_id"'; then
    SCAN_ID=$(echo "$SCAN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['scan_id'])" 2>/dev/null || echo "")
    _pass "POST /v1/scan → 202 Accepted (scan_id: $SCAN_ID)"

    echo ""
    echo "── Scan completion (polling) ─────────────────────"
    if [ -n "$SCAN_ID" ]; then
        STATUS=""
        for i in $(seq 1 30); do
            RECORD=$(curl -sf --max-time 10 "$BACKEND_URL/v1/scan/$SCAN_ID" 2>/dev/null || echo "")
            STATUS=$(echo "$RECORD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))" 2>/dev/null || echo "")
            if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then break; fi
            sleep 1
        done
        if [ "$STATUS" = "completed" ]; then
            _pass "Scan $SCAN_ID → completed"
        else
            _fail "Scan $SCAN_ID → status=$STATUS after 30s"
        fi
    fi
else
    _fail "POST /v1/scan → no scan_id in response: $SCAN_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Results: $PASS passed, $FAIL failed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ "$FAIL" -gt 0 ]; then exit 1; fi
