#!/usr/bin/env bash
# bridge-ingress watchdog: polls /healthz, alerts on state transitions.
#
# Reads env vars:
#   BRIDGE_HEALTHZ_URL         (default: http://bridge-ingress:8080/healthz)
#   ALERT_TELEGRAM_BOT_TOKEN   (required, from BotFather)
#   ALERT_TELEGRAM_CHAT_ID     (required, your private chat id)
#   CHECK_INTERVAL_SECONDS     (default: 60)
#   FAILURE_THRESHOLD          (default: 3)
#   LOG_LEVEL                  (info|debug, default: info)
#
# State machine:
#   unknown    -> healthy   on first ok check (info log only)
#   healthy    -> unhealthy after FAILURE_THRESHOLD consecutive failures (ALERT)
#   unhealthy  -> healthy   on first ok check after failures (RECOVERY ALERT)
#
# Never alerts twice for the same state. Restart resets state to unknown.
#
# ASCII-only.

set -uo pipefail

# --- Config ---
BRIDGE_HEALTHZ_URL="${BRIDGE_HEALTHZ_URL:-http://bridge-ingress:8080/healthz}"
ALERT_BOT_TOKEN="${ALERT_TELEGRAM_BOT_TOKEN:-}"
ALERT_CHAT_ID="${ALERT_TELEGRAM_CHAT_ID:-}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-60}"
FAILURE_THRESHOLD="${FAILURE_THRESHOLD:-3}"
LOG_LEVEL="${LOG_LEVEL:-info}"
WATCHDOG_VERSION="0.1.0"

# Source the alert helper (provides send_alert function).
# Use BASH_SOURCE[0] so this works whether run directly or sourced by tests.
_WATCHDOG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=alert.sh
. "${_WATCHDOG_DIR}/alert.sh"

# --- Logging ---
log() {
    local level="$1"
    shift
    if [ "$level" = "debug" ] && [ "$LOG_LEVEL" != "debug" ]; then
        return
    fi
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    # Single-line JSON log; field whitelist enforced manually below.
    printf '{"ts":"%s","level":"%s","logger":"watchdog","msg":"%s"}\n' \
        "$ts" "$level" "$*"
}

# --- Validation ---
# Returns 0 if env is valid, 1 otherwise. Caller decides whether to exit.
validate_env() {
    if [ -z "$ALERT_BOT_TOKEN" ]; then
        log error "missing_env ALERT_TELEGRAM_BOT_TOKEN"
        return 1
    fi
    if [ -z "$ALERT_CHAT_ID" ]; then
        log error "missing_env ALERT_TELEGRAM_CHAT_ID"
        return 1
    fi
    if ! command -v curl >/dev/null 2>&1; then
        log error "missing_dep curl"
        return 1
    fi
    if ! command -v jq >/dev/null 2>&1; then
        log error "missing_dep jq"
        return 1
    fi
    return 0
}

# --- Health check ---
# Sets globals: CHECK_OK ("yes"/"no"), CHECK_REASON, CHECK_LAST_ERROR
check_health() {
    CHECK_OK="no"
    CHECK_REASON=""
    CHECK_LAST_ERROR=""

    local body
    local http_code
    local tmpfile
    tmpfile="$(mktemp)"

    http_code="$(
        curl -fsS -o "$tmpfile" -w '%{http_code}' \
            --max-time 10 \
            "$BRIDGE_HEALTHZ_URL" 2>/dev/null
    )" || true

    if [ -z "$http_code" ] || [ "$http_code" = "000" ]; then
        CHECK_REASON="http_unreachable"
        rm -f "$tmpfile"
        return
    fi

    if [ "$http_code" != "200" ]; then
        CHECK_REASON="http_${http_code}"
        rm -f "$tmpfile"
        return
    fi

    body="$(cat "$tmpfile")"
    rm -f "$tmpfile"

    local listener_connected
    listener_connected="$(echo "$body" | jq -r '.listener_connected' 2>/dev/null)" || true
    if [ "$listener_connected" != "true" ]; then
        CHECK_REASON="listener_disconnected"
        CHECK_LAST_ERROR="$(echo "$body" | jq -r '.last_error // ""' 2>/dev/null)"
        return
    fi

    CHECK_OK="yes"
}

# --- Main loop ---
main() {
    if ! validate_env; then
        exit 1
    fi
    log info "watchdog_starting version=$WATCHDOG_VERSION url=$BRIDGE_HEALTHZ_URL"

    local state="unknown"
    local consecutive_failures=0
    local unhealthy_since=""

    while true; do
        check_health

        if [ "$CHECK_OK" = "yes" ]; then
            log debug "check_ok state=$state failures=$consecutive_failures"
            consecutive_failures=0

            if [ "$state" = "unhealthy" ]; then
                local now downtime_min
                now="$(date -u +%s)"
                downtime_min=$(( (now - unhealthy_since) / 60 ))
                send_recovery_alert "$downtime_min"
                log info "state_transition unhealthy_to_healthy downtime_min=$downtime_min"
                state="healthy"
                unhealthy_since=""
            elif [ "$state" = "unknown" ]; then
                log info "initial_state_healthy"
                state="healthy"
            fi
        else
            consecutive_failures=$((consecutive_failures + 1))
            log info "check_failed reason=$CHECK_REASON failures=$consecutive_failures threshold=$FAILURE_THRESHOLD"

            if [ "$state" != "unhealthy" ] \
                && [ "$consecutive_failures" -ge "$FAILURE_THRESHOLD" ]; then
                unhealthy_since="$(date -u +%s)"
                send_unhealthy_alert "$CHECK_REASON" "$CHECK_LAST_ERROR"
                log info "state_transition_to_unhealthy reason=$CHECK_REASON"
                state="unhealthy"
            fi
        fi

        sleep "$CHECK_INTERVAL_SECONDS"
    done
}

# Allow sourcing this script for tests without running main.
if [ "${WATCHDOG_TEST_MODE:-}" != "1" ]; then
    main
fi
