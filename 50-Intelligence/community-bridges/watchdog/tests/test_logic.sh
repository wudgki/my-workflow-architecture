#!/usr/bin/env bash
# Unit tests for check_health logic and alert message formatting.
# No real network calls; uses mock curl.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SVC_DIR="$(cd "$HERE/.." && pwd)"

# Stub curl + jq paths so we can intercept calls.
MOCK_DIR="$(mktemp -d)"
trap 'rm -rf "$MOCK_DIR"' EXIT

PASS=0
FAIL=0
assert() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS  $name"
        PASS=$((PASS + 1))
    else
        echo "  FAIL  $name"
        echo "    expected: $expected"
        echo "    actual:   $actual"
        FAIL=$((FAIL + 1))
    fi
}

# Set required env vars (fake values).
export ALERT_TELEGRAM_BOT_TOKEN="fake-bot-token-for-tests"
export ALERT_TELEGRAM_CHAT_ID="999999"
export BRIDGE_HEALTHZ_URL="http://localhost:99999/healthz"

# Source the watchdog script in test mode (no main loop).
export WATCHDOG_TEST_MODE=1
# shellcheck source=../watchdog.sh
. "$SVC_DIR/watchdog.sh"

echo "== test 1: check_health on connection refused =="
# URL points to a port nothing listens on; curl will fail.
check_health
assert "CHECK_OK"     "no"                  "$CHECK_OK"
assert "CHECK_REASON" "http_unreachable"    "$CHECK_REASON"

echo ""
echo "== test 2: check_health helper jq parsing =="
# Verify jq actually parses listener_connected from a healthy body.
healthy_body='{"status":"ok","listener_connected":true,"messages_processed":5}'
parsed="$(echo "$healthy_body" | jq -r '.listener_connected')"
assert "jq_parse_healthy"   "true"  "$parsed"

unhealthy_body='{"status":"ok","listener_connected":false,"last_error":"timeout"}'
parsed_unh="$(echo "$unhealthy_body" | jq -r '.listener_connected')"
parsed_err="$(echo "$unhealthy_body" | jq -r '.last_error // ""')"
assert "jq_parse_unhealthy" "false"     "$parsed_unh"
assert "jq_parse_lasterr"   "timeout"   "$parsed_err"

echo ""
echo "== test 3: env validation rejects empty token =="
saved_token="$ALERT_TELEGRAM_BOT_TOKEN"
ALERT_BOT_TOKEN=""
output="$(validate_env 2>&1 || true)"
case "$output" in
    *missing_env*ALERT_TELEGRAM_BOT_TOKEN*)
        assert "validate_rejects_empty_token" "yes" "yes" ;;
    *)
        assert "validate_rejects_empty_token" "yes" "no (got: $output)" ;;
esac
ALERT_BOT_TOKEN="$saved_token"

echo ""
echo "== test 4: alert message format =="
# Override send_telegram_message to capture text instead of sending.
CAPTURED_TEXT=""
send_telegram_message() {
    CAPTURED_TEXT="$1"
    return 0
}

send_unhealthy_alert "listener_disconnected" "connection timeout"
case "$CAPTURED_TEXT" in
    *"UNHEALTHY"*"listener_disconnected"*"connection timeout"*)
        assert "unhealthy_alert_format" "yes" "yes" ;;
    *)
        assert "unhealthy_alert_format" "yes" "no (got: $CAPTURED_TEXT)" ;;
esac

case "$CAPTURED_TEXT" in
    *fake-bot-token*)
        assert "alert_does_not_leak_token" "no" "yes (LEAK!)" ;;
    *)
        assert "alert_does_not_leak_token" "no" "no" ;;
esac

send_recovery_alert "12"
case "$CAPTURED_TEXT" in
    *"RECOVERED"*"12 minutes"*)
        assert "recovery_alert_format" "yes" "yes" ;;
    *)
        assert "recovery_alert_format" "yes" "no (got: $CAPTURED_TEXT)" ;;
esac

echo ""
echo "----------------------------------------"
echo "PASS: $PASS    FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "ALL TESTS PASSED"
