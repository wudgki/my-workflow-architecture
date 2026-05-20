#!/usr/bin/env bash
# Verify alert.sh syntax and that it does not leak the token to logs.
# Does NOT make real Telegram API calls.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SVC_DIR="$(cd "$HERE/.." && pwd)"

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

echo "== test: bash -n syntax check =="
if bash -n "$SVC_DIR/watchdog.sh" 2>&1; then
    assert "watchdog.sh syntax" "ok" "ok"
else
    assert "watchdog.sh syntax" "ok" "fail"
fi

if bash -n "$SVC_DIR/alert.sh" 2>&1; then
    assert "alert.sh syntax" "ok" "ok"
else
    assert "alert.sh syntax" "ok" "fail"
fi

echo ""
echo "== test: alert.sh does not contain real-looking secrets =="
# The script should never have a string matching a Telegram token pattern.
# Real tokens look like: digits:base64chars (e.g. 1234567:AAH...).
# We grep for that pattern; any match would be suspicious.
if grep -E '[0-9]{8,}:[A-Za-z0-9_-]{30,}' "$SVC_DIR/alert.sh" > /dev/null; then
    assert "alert.sh has no token-like literal" "yes" "no (LEAK!)"
else
    assert "alert.sh has no token-like literal" "yes" "yes"
fi

if grep -E '[0-9]{8,}:[A-Za-z0-9_-]{30,}' "$SVC_DIR/watchdog.sh" > /dev/null; then
    assert "watchdog.sh has no token-like literal" "yes" "no (LEAK!)"
else
    assert "watchdog.sh has no token-like literal" "yes" "yes"
fi

echo ""
echo "== test: scripts are ASCII-only =="
# Use python (always available in any reasonable dev env) to count
# non-ASCII bytes precisely. wc -l on grep -P output is unreliable
# across BusyBox / GNU grep.
non_ascii_w="$(python3 -c "import sys; print(sum(1 for b in open(sys.argv[1],'rb').read() if b > 127))" "$SVC_DIR/watchdog.sh")"
non_ascii_a="$(python3 -c "import sys; print(sum(1 for b in open(sys.argv[1],'rb').read() if b > 127))" "$SVC_DIR/alert.sh")"
assert "watchdog.sh ASCII-only" "0" "$non_ascii_w"
assert "alert.sh ASCII-only"    "0" "$non_ascii_a"

echo ""
echo "----------------------------------------"
echo "PASS: $PASS    FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
echo "ALL TESTS PASSED"
