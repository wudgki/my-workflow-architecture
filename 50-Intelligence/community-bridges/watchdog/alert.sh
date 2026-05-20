#!/usr/bin/env bash
# Telegram Bot API alert sender.
#
# Functions:
#   send_unhealthy_alert <reason> [last_error]
#   send_recovery_alert <downtime_minutes>
#   send_telegram_message <text>      (raw, used by the above)
#
# NEVER prints the bot token or chat id to stdout/logs.
# ASCII-only.

# Send a raw text message to ALERT_CHAT_ID using ALERT_BOT_TOKEN.
# Uses the Bot API sendMessage endpoint.
send_telegram_message() {
    local text="$1"
    local api_url="https://api.telegram.org/bot${ALERT_BOT_TOKEN}/sendMessage"

    # POST as form-encoded; do NOT log the URL (contains the token).
    local http_code
    http_code="$(
        curl -fsS -o /dev/null -w '%{http_code}' \
            --max-time 10 \
            -X POST "$api_url" \
            --data-urlencode "chat_id=${ALERT_CHAT_ID}" \
            --data-urlencode "text=${text}" \
            --data-urlencode "disable_web_page_preview=true" 2>/dev/null
    )" || true

    if [ "$http_code" = "200" ]; then
        log info "alert_sent http_code=200"
        return 0
    fi
    # Log the failure but never the token.
    log error "alert_send_failed http_code=${http_code:-none}"
    return 1
}

# Send the "bridge unhealthy" alert.
send_unhealthy_alert() {
    local reason="$1"
    local last_error="${2:-}"
    local ts
    ts="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

    local body
    body="[Hermes VPS] bridge-ingress UNHEALTHY"$'\n'
    body+="time: ${ts}"$'\n'
    body+="reason: ${reason}"
    if [ -n "$last_error" ]; then
        body+=$'\n'"last_error: ${last_error}"
    fi
    body+=$'\n'"action: SSH to VPS, check 'docker logs hermes-bridge-ingress'"

    send_telegram_message "$body"
}

# Send the "bridge recovered" alert.
send_recovery_alert() {
    local downtime_min="$1"
    local ts
    ts="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

    local body
    body="[Hermes VPS] bridge-ingress RECOVERED"$'\n'
    body+="time: ${ts}"$'\n'
    body+="downtime: ${downtime_min} minutes"

    send_telegram_message "$body"
}
