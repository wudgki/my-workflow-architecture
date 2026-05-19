#!/usr/bin/env bash
# bridge-ingress local smoke test.
#
# WARNING: For local developer machines ONLY. Do NOT run on the VPS.
# This script builds an image, exposes :8080 on localhost, and starts a
# container with a fake secret. The corresponding human-facing runbook is
# 90-Ops/runbook/telegram-bridge-smoke-test.md.
#
# Exit code 0 = all checks passed. Any other exit = failure on the
# corresponding step.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SVC_DIR="$(cd "$HERE/.." && pwd)"
REPO_ROOT="$(cd "$SVC_DIR/../../.." && pwd)"

IMAGE="bridge-ingress:smoke"
CONTAINER="bridge-ingress-smoke"
SECRET="fake-secret-for-smoke-test"
PORT="${PORT:-8080}"
INBOX="$(mktemp -d -t bridge-inbox-XXXXXX)"

cleanup() {
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    rm -rf "$INBOX"
}
trap cleanup EXIT

KEYWORDS_HOST="$REPO_ROOT/50-Intelligence/pipelines/keywords.yaml"
if [ ! -f "$KEYWORDS_HOST" ]; then
    echo "FAIL keywords.yaml not found at $KEYWORDS_HOST" >&2
    exit 2
fi

echo "[1/7] docker build -> $IMAGE"
docker build -t "$IMAGE" "$SVC_DIR" >/dev/null

echo "[2/7] docker run $CONTAINER on :$PORT (inbox=$INBOX)"
docker run -d --name "$CONTAINER" \
    -e TELEGRAM_WEBHOOK_SECRET="$SECRET" \
    -e LOG_LEVEL=info \
    -p "$PORT:8080" \
    -v "$INBOX:/data/inbox" \
    -v "$KEYWORDS_HOST:/blueprint/50-Intelligence/pipelines/keywords.yaml:ro" \
    "$IMAGE" >/dev/null

# Wait up to 15s for /healthz to come up.
for _ in $(seq 1 15); do
    if curl -fsS "http://localhost:$PORT/healthz" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "[3/7] GET /healthz -> expect 200"
code="$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/healthz")"
if [ "$code" != "200" ]; then
    echo "FAIL healthz: got $code" >&2
    docker logs "$CONTAINER" >&2 || true
    exit 3
fi

echo "[4/7] POST /webhook/telegram with WRONG secret -> expect 401"
code="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    -H 'X-Telegram-Bot-Api-Secret-Token: WRONG' \
    -H 'Content-Type: application/json' \
    -d '{"update_id":1}' \
    "http://localhost:$PORT/webhook/telegram")"
if [ "$code" != "401" ]; then
    echo "FAIL wrong secret: got $code" >&2
    exit 4
fi

echo "[5/7] POST /webhook/telegram with CORRECT secret + valid update -> expect 200"
code="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    -H "X-Telegram-Bot-Api-Secret-Token: $SECRET" \
    -H 'Content-Type: application/json' \
    --data-binary "@$HERE/fixtures/telegram_btc_signal.json" \
    "http://localhost:$PORT/webhook/telegram")"
if [ "$code" != "200" ]; then
    echo "FAIL valid update: got $code" >&2
    docker logs "$CONTAINER" >&2 || true
    exit 5
fi

echo "[6/7] verify inbox file landed in $INBOX/Telegram-Captures/"
shopt -s nullglob
files=("$INBOX"/Telegram-Captures/*.md)
if [ "${#files[@]}" -eq 0 ]; then
    echo "FAIL no .md file produced" >&2
    docker logs "$CONTAINER" >&2 || true
    exit 6
fi
echo "    -> ${files[0]}"

echo "[7/7] verify front-matter contains chat_id, message_id, phase"
grep -q "^chat_id:" "${files[0]}"     || { echo "FAIL chat_id missing"     >&2; exit 7; }
grep -q "^message_id:" "${files[0]}"  || { echo "FAIL message_id missing"  >&2; exit 7; }
grep -q "^phase:" "${files[0]}"       || { echo "FAIL phase missing"       >&2; exit 7; }
grep -q "^source: telegram"           "${files[0]}" || { echo "FAIL source field missing" >&2; exit 7; }

echo
echo "SMOKE TEST PASSED"
