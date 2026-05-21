#!/bin/bash
# rsync-captures-guard.sh
#
# Restricted SSH forced-command wrapper for VPS authorized_keys.
# Validates that the incoming SSH_ORIGINAL_COMMAND is a legitimate
# rsync --server --sender request targeting ONLY the allowed path.
#
# Usage in ~/.ssh/authorized_keys:
#   restrict,command="/root/.ssh/rsync-captures-guard.sh" ssh-ed25519 AAAA...
#
# Security properties:
#   - Only allows rsync --server --sender (read-only transfer to client)
#   - Source path must end with /data/inbox/Telegram-Captures/
#   - Rejects shell metacharacters (;|&`$(){}[]<>!)
#   - Executes the validated command as an argv array (no eval/sh -c)
#   - Logs the original command + timestamp for debugging
#   - Never logs SSH keys, tokens, or secrets
#
# This approach is rsync-version-agnostic: it does not hardcode the
# exact flags (e.g. -logDtprze.iLsfxCIvu) which change between rsync
# versions, --dry-run, --progress, etc. It only validates the structural
# pattern: rsync --server --sender <flags> . <allowed-path>
#
# ASCII-only. Deploy to /root/.ssh/rsync-captures-guard.sh on VPS.

set -uo pipefail

ALLOWED_PATH="/data/inbox/Telegram-Captures/"
LOG_FILE="/tmp/hermes-rsync-original-command.log"

# --- Logging (never logs secrets) ---
log() {
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "${ts} $*" >> "$LOG_FILE"
}

# --- Reject helper ---
reject() {
    log "REJECTED: $1 | cmd=$SSH_ORIGINAL_COMMAND"
    echo "ERROR: $1" >&2
    exit 1
}

# --- Validate SSH_ORIGINAL_COMMAND ---
if [ -z "${SSH_ORIGINAL_COMMAND:-}" ]; then
    reject "no SSH_ORIGINAL_COMMAND (interactive shell not allowed)"
fi

log "RECEIVED: $SSH_ORIGINAL_COMMAND"

# Check 1: must start with "rsync --server --sender"
case "$SSH_ORIGINAL_COMMAND" in
    "rsync --server --sender "*)
        ;;
    *)
        reject "command does not start with 'rsync --server --sender'"
        ;;
esac

# Check 2: reject shell metacharacters
# These should never appear in a legitimate rsync --server command.
if echo "$SSH_ORIGINAL_COMMAND" | grep -qE '[;|&`$\(\)\{\}\[\]<>!]'; then
    reject "shell metacharacters detected"
fi

# Check 3: the command must contain the allowed path as the final argument
# rsync --server --sender <flags> . <path>
# The path is always the last space-separated token.
LAST_ARG="${SSH_ORIGINAL_COMMAND##* }"

if [ "$LAST_ARG" != "$ALLOWED_PATH" ] && \
   [ "$LAST_ARG" != "${ALLOWED_PATH%/}" ]; then
    reject "source path '$LAST_ARG' not allowed (expected $ALLOWED_PATH)"
fi

# Check 4: must contain " . " before the path (rsync protocol separator)
if ! echo "$SSH_ORIGINAL_COMMAND" | grep -qF " . "; then
    reject "missing rsync path separator ' . '"
fi

# --- Execute validated command ---
# Use exec with word splitting (safe here because we already rejected
# metacharacters above). This preserves rsync's expected argv layout.
log "ALLOWED: executing"
exec $SSH_ORIGINAL_COMMAND
